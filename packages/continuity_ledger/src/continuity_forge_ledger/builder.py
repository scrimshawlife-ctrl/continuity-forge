"""Deterministic continuity ledger builder over validated Production IR."""

from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID

from continuity_forge_ir import (
    AtomType,
    CompileDiagnostic,
    DiagnosticSeverity,
    NarrativeAtom,
    ScriptDocument,
    stable_id,
)

from .models import (
    ContinuityFact,
    ContinuityLedger,
    Entity,
    EntityKind,
    EvidenceGrade,
    FactKind,
    SceneContinuityContract,
    SetupPayoffLink,
)

SCENE_PREFIX_RE = re.compile(
    r"^(?:INT\.|EXT\.|EST\.|INT/EXT\.|INT\./EXT\.|I/E\.)\s*",
    re.IGNORECASE,
)
TIME_SUFFIX_RE = re.compile(
    r"\s*-\s*(DAY|NIGHT|DAWN|DUSK|MORNING|EVENING|LATER|CONTINUOUS|PRESENT|FLASHBACK.*)$",
    re.IGNORECASE,
)
CHARACTER_EXTENSION_RE = re.compile(r"\s*\([^)]*\)\s*$")
ENTER_RE = re.compile(
    r"\b([A-Z][a-z]+|[A-Z]{2,})\s+(re-?enters|enters)\b",
    re.IGNORECASE,
)
EXIT_RE = re.compile(
    r"\b([A-Z][a-z]+|[A-Z]{2,})\s+exits\b",
    re.IGNORECASE,
)
ABSENT_RE = re.compile(
    r"\b(gone|vanished|missing|no longer|disappeared)\b",
    re.IGNORECASE,
)
PLANT_RE = re.compile(r"\bplant\b", re.IGNORECASE)
PAYOFF_RE = re.compile(r"\bpayoff\b", re.IGNORECASE)

# Ordered longest-first so multiword phrases win over substrings.
TRACKED_ITEMS: tuple[tuple[EntityKind, str, re.Pattern[str]], ...] = (
    (EntityKind.PROP, "red keycard", re.compile(r"\bred\s+keycard\b", re.IGNORECASE)),
    (EntityKind.PROP, "brass compass", re.compile(r"\bbrass\s+compass\b", re.IGNORECASE)),
    (EntityKind.PROP, "keycard", re.compile(r"\bkeycard\b", re.IGNORECASE)),
    (EntityKind.PROP, "compass", re.compile(r"\bcompass\b", re.IGNORECASE)),
    (EntityKind.WARDROBE, "jacket", re.compile(r"\bjacket\b", re.IGNORECASE)),
    (
        EntityKind.INJURY,
        "forearm cut",
        re.compile(
            r"\b(?:left\s+)?forearm\b.*\b(?:cut|wound|injury)\b|"
            r"\b(?:cut|wound|injury)\b.*\b(?:left\s+)?forearm\b|"
            r"\bthin cut\b|\bwound\b",
            re.IGNORECASE,
        ),
    ),
)

WARDROBE_STATE_RE = re.compile(
    r"\b(unbloodied|clean|torn|navy|black|grey|gray|intact)\b",
    re.IGNORECASE,
)
INJURY_STATE_RE = re.compile(
    r"\b(thin cut|deeper|visible|glances|injury plant)\b",
    re.IGNORECASE,
)


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _character_base_name(cue: str) -> str:
    return CHARACTER_EXTENSION_RE.sub("", cue).strip()


def _location_from_slugline(slugline: str) -> str:
    remainder = SCENE_PREFIX_RE.sub("", slugline).strip()
    remainder = TIME_SUFFIX_RE.sub("", remainder).strip(" -")
    return remainder or slugline


def build_continuity_ledger(document: ScriptDocument) -> ContinuityLedger:
    """Derive a continuity ledger from a validated Production IR document."""
    entities: dict[tuple[EntityKind, str], Entity] = {}
    facts: list[ContinuityFact] = []
    diagnostics: list[CompileDiagnostic] = []
    scene_fact_ids: dict[UUID, list[UUID]] = defaultdict(list)
    character_names: dict[str, UUID] = {}

    def ensure_entity(
        kind: EntityKind,
        name: str,
        *,
        scene_id: UUID | None,
        alias: str | None = None,
    ) -> Entity:
        key = (kind, _normalized(name))
        existing = entities.get(key)
        if existing is not None:
            if (
                alias
                and alias not in existing.aliases
                and _normalized(alias) != existing.normalized_name
            ):
                existing.aliases.append(alias)
            if existing.first_scene_id is None and scene_id is not None:
                existing.first_scene_id = scene_id
            return existing
        entity = Entity(
            entity_id=stable_id("entity", document.script_id, kind.value, _normalized(name)),
            kind=kind,
            name=name,
            normalized_name=_normalized(name),
            first_scene_id=scene_id,
            aliases=[alias] if alias and _normalized(alias) != _normalized(name) else [],
        )
        entities[key] = entity
        return entity

    def add_fact(
        *,
        kind: FactKind,
        subject: Entity,
        scene_id: UUID | None,
        atom: NarrativeAtom,
        value: str,
        evidence: EvidenceGrade,
        object_entity: Entity | None = None,
    ) -> ContinuityFact:
        fact = ContinuityFact(
            fact_id=stable_id(
                "fact",
                document.script_id,
                kind.value,
                subject.entity_id,
                scene_id or "none",
                atom.atom_id,
                _normalized(value),
            ),
            kind=kind,
            subject_entity_id=subject.entity_id,
            object_entity_id=object_entity.entity_id if object_entity else None,
            scene_id=scene_id,
            atom_ids=[atom.atom_id],
            value=value,
            evidence=evidence,
            source_span=atom.source_span,
        )
        facts.append(fact)
        if scene_id is not None:
            scene_fact_ids[scene_id].append(fact.fact_id)
        return fact

    # Character entities from cues.
    for scene in document.scenes:
        for atom in scene.atoms:
            if atom.type != AtomType.CHARACTER:
                continue
            base = _character_base_name(atom.text)
            entity = ensure_entity(
                EntityKind.CHARACTER, base, scene_id=scene.scene_id, alias=atom.text
            )
            character_names[_normalized(base)] = entity.entity_id
            character_names[_normalized(atom.text)] = entity.entity_id
            add_fact(
                kind=FactKind.APPEARS_IN,
                subject=entity,
                scene_id=scene.scene_id,
                atom=atom,
                value=scene.slugline,
                evidence=EvidenceGrade.DETERMINISTIC,
            )

    scene_contracts: list[SceneContinuityContract] = []
    plant_facts: list[ContinuityFact] = []
    payoff_facts: list[ContinuityFact] = []

    for scene in document.scenes:
        location_name = _location_from_slugline(scene.slugline)
        location = ensure_entity(EntityKind.LOCATION, location_name, scene_id=scene.scene_id)
        present: set[UUID] = set()
        entries: set[UUID] = set()
        exits: set[UUID] = set()
        props: set[UUID] = set()
        wardrobe: set[UUID] = set()
        injuries: set[UUID] = set()
        last_present_prop: Entity | None = None

        for atom in scene.atoms:
            if atom.type == AtomType.CHARACTER:
                base = _character_base_name(atom.text)
                present.add(character_names[_normalized(base)])
                continue

            if atom.type not in {
                AtomType.ACTION,
                AtomType.DIALOGUE,
                AtomType.NOTE,
                AtomType.SYNOPSIS,
            }:
                continue

            text = atom.text
            atom_present_props: list[Entity] = []

            for match in ENTER_RE.finditer(text):
                who = match.group(1)
                entity = ensure_entity(
                    EntityKind.CHARACTER,
                    who.title() if who.islower() else who,
                    scene_id=scene.scene_id,
                )
                character_names[_normalized(entity.name)] = entity.entity_id
                present.add(entity.entity_id)
                entries.add(entity.entity_id)
                add_fact(
                    kind=FactKind.ENTERS,
                    subject=entity,
                    scene_id=scene.scene_id,
                    atom=atom,
                    value=match.group(0),
                    evidence=EvidenceGrade.HEURISTIC,
                )

            for match in EXIT_RE.finditer(text):
                who = match.group(1)
                entity = ensure_entity(
                    EntityKind.CHARACTER,
                    who.title() if who.islower() else who,
                    scene_id=scene.scene_id,
                )
                character_names[_normalized(entity.name)] = entity.entity_id
                present.add(entity.entity_id)
                exits.add(entity.entity_id)
                add_fact(
                    kind=FactKind.EXITS,
                    subject=entity,
                    scene_id=scene.scene_id,
                    atom=atom,
                    value=match.group(0),
                    evidence=EvidenceGrade.HEURISTIC,
                )

            for kind, name, pattern in TRACKED_ITEMS:
                if not pattern.search(text):
                    continue
                # Skip short form if long form also matches in same atom.
                if name in {"keycard", "compass"}:
                    long_form = f"red {name}" if name == "keycard" else f"brass {name}"
                    long_pat = next(p for _k, n, p in TRACKED_ITEMS if n == long_form)
                    if long_pat.search(text):
                        continue

                entity = ensure_entity(kind, name, scene_id=scene.scene_id)
                short = re.escape(name.split()[-1])
                item_absent = bool(
                    re.search(
                        rf"\b{re.escape(name)}\b[^.]*\b(gone|vanished|missing)\b|"
                        rf"\b(gone|vanished|missing)\b[^.]*\b{re.escape(name)}\b|"
                        rf"\bno\s+{short}\b",
                        text,
                        re.IGNORECASE,
                    )
                )
                if kind == EntityKind.PROP:
                    props.add(entity.entity_id)
                    if item_absent:
                        fact_kind = FactKind.ABSENT
                        value = f"{name} absent"
                    else:
                        fact_kind = FactKind.HOLDS
                        value = name
                        atom_present_props.append(entity)
                        last_present_prop = entity
                elif kind == EntityKind.WARDROBE:
                    wardrobe.add(entity.entity_id)
                    fact_kind = FactKind.WEARS
                    state = WARDROBE_STATE_RE.search(text)
                    value = f"{name}:{state.group(1).casefold()}" if state else name
                else:
                    injuries.add(entity.entity_id)
                    fact_kind = FactKind.INJURED
                    state = INJURY_STATE_RE.search(text)
                    value = f"{name}:{state.group(1).casefold()}" if state else name

                add_fact(
                    kind=fact_kind,
                    subject=entity,
                    scene_id=scene.scene_id,
                    atom=atom,
                    value=value,
                    evidence=EvidenceGrade.HEURISTIC,
                )

            if PLANT_RE.search(text):
                subject = last_present_prop or ensure_entity(
                    EntityKind.PROP, "planted element", scene_id=scene.scene_id
                )
                plant = add_fact(
                    kind=FactKind.PLANTS,
                    subject=subject,
                    scene_id=scene.scene_id,
                    atom=atom,
                    value=text.strip(),
                    evidence=EvidenceGrade.HEURISTIC,
                )
                plant_facts.append(plant)
                if subject.kind == EntityKind.PROP:
                    props.add(subject.entity_id)

            if PAYOFF_RE.search(text):
                payoff_subjects = atom_present_props or (
                    [last_present_prop] if last_present_prop is not None else []
                )
                if not payoff_subjects:
                    payoff_subjects = [
                        ensure_entity(EntityKind.PROP, "payoff element", scene_id=scene.scene_id)
                    ]
                for subject in payoff_subjects:
                    payoff = add_fact(
                        kind=FactKind.PAYS_OFF,
                        subject=subject,
                        scene_id=scene.scene_id,
                        atom=atom,
                        value=text.strip(),
                        evidence=EvidenceGrade.HEURISTIC,
                    )
                    payoff_facts.append(payoff)
                    if subject.kind == EntityKind.PROP:
                        props.add(subject.entity_id)

        scene_contracts.append(
            SceneContinuityContract(
                scene_id=scene.scene_id,
                ordinal=scene.ordinal,
                slugline=scene.slugline,
                location_entity_id=location.entity_id,
                characters_present=sorted(present, key=str),
                entries=sorted(entries, key=str),
                exits=sorted(exits, key=str),
                props_referenced=sorted(props, key=str),
                wardrobe_referenced=sorted(wardrobe, key=str),
                injuries_referenced=sorted(injuries, key=str),
                fact_ids=list(scene_fact_ids.get(scene.scene_id, [])),
            )
        )

    # Deterministic setup/payoff links: same entity, setup scene before payoff scene.
    links: list[SetupPayoffLink] = []
    used_payoffs: set[UUID] = set()
    for plant in plant_facts:
        for payoff in payoff_facts:
            if payoff.fact_id in used_payoffs:
                continue
            if plant.subject_entity_id != payoff.subject_entity_id:
                continue
            if plant.scene_id is None or payoff.scene_id is None:
                continue
            plant_ord = next(c.ordinal for c in scene_contracts if c.scene_id == plant.scene_id)
            payoff_ord = next(c.ordinal for c in scene_contracts if c.scene_id == payoff.scene_id)
            if payoff_ord < plant_ord:
                continue
            links.append(
                SetupPayoffLink(
                    link_id=stable_id(
                        "setup_payoff",
                        document.script_id,
                        plant.fact_id,
                        payoff.fact_id,
                    ),
                    entity_id=plant.subject_entity_id,
                    setup_fact_id=plant.fact_id,
                    payoff_fact_id=payoff.fact_id,
                    setup_scene_id=plant.scene_id,
                    payoff_scene_id=payoff.scene_id,
                )
            )
            used_payoffs.add(payoff.fact_id)
            break

    if not any(entity.kind == EntityKind.CHARACTER for entity in entities.values()):
        diagnostics.append(
            CompileDiagnostic(
                code="CL100",
                severity=DiagnosticSeverity.WARNING,
                message="No character entities were derived from the Production IR.",
            )
        )

    # Stable ordering for deterministic serialization.
    ordered_entities = sorted(entities.values(), key=lambda e: (e.kind.value, e.normalized_name))
    ordered_facts = sorted(
        facts, key=lambda f: (str(f.scene_id), f.kind.value, f.value, str(f.fact_id))
    )
    ordered_links = sorted(links, key=lambda link: str(link.link_id))

    return ContinuityLedger(
        script_id=document.script_id,
        revision=document.revision,
        source_hash=document.source_hash,
        entities=ordered_entities,
        facts=ordered_facts,
        scene_contracts=scene_contracts,
        setup_payoff_links=ordered_links,
        diagnostics=diagnostics,
    )
