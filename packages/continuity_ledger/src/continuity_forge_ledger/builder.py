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
# Case-sensitive on the actor token so "and exits" is not a character cue.
ENTER_RE = re.compile(r"\b([A-Z][a-z]+|[A-Z]{2,})\s+(?:re-?enters|enters)\b")
# Allow short intervening action between the actor and "exits".
EXIT_RE = re.compile(r"\b([A-Z][a-z]+|[A-Z]{2,})\b(?:[^.\n]{0,60}?)\bexits\b")
NAME_STOPWORDS = frozenset({"and", "then", "but", "the", "she", "he", "they", "who", "as"})
TRANSITIONISH_NAME_RE = re.compile(
    r"^(?:BACK TO|CUT TO|FADE (?:IN|OUT)|DISSOLVE TO|SMASH CUT)\b",
    re.IGNORECASE,
)
PLANT_RE = re.compile(r"\bplant\b", re.IGNORECASE)
PAYOFF_RE = re.compile(r"\bpayoff\b", re.IGNORECASE)

# Canonical tracked lexicon: patterns may match short forms; names are canonical.
TRACKED_ITEMS: tuple[tuple[EntityKind, str, re.Pattern[str]], ...] = (
    (
        EntityKind.PROP,
        "red keycard",
        re.compile(r"\bred\s+keycard\b|\bkeycard\b", re.IGNORECASE),
    ),
    (
        EntityKind.PROP,
        "brass compass",
        re.compile(r"\bbrass\s+compass\b|\bcompass\b", re.IGNORECASE),
    ),
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


def _item_absent(name: str, text: str) -> bool:
    short = re.escape(name.split()[-1])
    return bool(
        re.search(
            rf"\b{re.escape(name)}\b[^.]*\b(gone|vanished|missing)\b|"
            rf"\b(gone|vanished|missing)\b[^.]*\b{re.escape(name)}\b|"
            rf"\bno\s+{short}\b|"
            rf"\b{short}\b[^.]*\b(gone|vanished|missing)\b|"
            rf"\b(gone|vanished|missing)\b[^.]*\b{short}\b",
            text,
            re.IGNORECASE,
        )
    )


def _resolve_character_name(
    who: str, known: dict[str, UUID], entities: dict[tuple[EntityKind, str], Entity]
) -> str:
    """Prefer an existing character entity's display name when casings differ."""
    norm = _normalized(who)
    if norm in known:
        for (kind, key), entity in entities.items():
            if kind == EntityKind.CHARACTER and key == norm:
                return entity.name
    # Prefer uppercase cue style for all-caps names under 3 tokens.
    if who.isupper() or who.islower():
        return who.upper() if len(who.split()) <= 3 else who.title()
    return who


def build_continuity_ledger(document: ScriptDocument) -> ContinuityLedger:
    """Derive a continuity ledger from a validated Production IR document."""
    entities: dict[tuple[EntityKind, str], Entity] = {}
    facts: list[ContinuityFact] = []
    diagnostics: list[CompileDiagnostic] = []
    scene_fact_ids: dict[UUID, list[UUID]] = defaultdict(list)
    character_names: dict[str, UUID] = {}
    scene_ordinals = {scene.scene_id: scene.ordinal for scene in document.scenes}

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

    # Character entities from cues first (deterministic identity anchors).
    for scene in document.scenes:
        for atom in scene.atoms:
            if atom.type != AtomType.CHARACTER:
                continue
            base = _character_base_name(atom.text)
            if TRANSITIONISH_NAME_RE.match(base):
                # Fountain uppercase transitions are sometimes tokenized as cues.
                continue
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
                if TRANSITIONISH_NAME_RE.match(base):
                    continue
                entity_id = character_names.get(_normalized(base))
                if entity_id is not None:
                    present.add(entity_id)
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
                raw_who = match.group(1)
                if _normalized(raw_who) in NAME_STOPWORDS:
                    continue
                who = _resolve_character_name(raw_who, character_names, entities)
                entity = ensure_entity(
                    EntityKind.CHARACTER,
                    who,
                    scene_id=scene.scene_id,
                    alias=raw_who,
                )
                character_names[_normalized(entity.name)] = entity.entity_id
                character_names[_normalized(raw_who)] = entity.entity_id
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
                raw_who = match.group(1)
                if _normalized(raw_who) in NAME_STOPWORDS:
                    continue
                who = _resolve_character_name(raw_who, character_names, entities)
                entity = ensure_entity(
                    EntityKind.CHARACTER,
                    who,
                    scene_id=scene.scene_id,
                    alias=raw_who,
                )
                character_names[_normalized(entity.name)] = entity.entity_id
                character_names[_normalized(raw_who)] = entity.entity_id
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
                entity = ensure_entity(kind, name, scene_id=scene.scene_id)
                if kind == EntityKind.PROP:
                    props.add(entity.entity_id)
                    if _item_absent(name, text):
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

    links = _link_setup_payoff(document.script_id, plant_facts, payoff_facts, scene_contracts)
    diagnostics.extend(_drift_diagnostics(facts, entities, scene_ordinals))

    if not any(entity.kind == EntityKind.CHARACTER for entity in entities.values()):
        diagnostics.append(
            CompileDiagnostic(
                code="CL100",
                severity=DiagnosticSeverity.WARNING,
                message="No character entities were derived from the Production IR.",
            )
        )

    ordered_entities = sorted(entities.values(), key=lambda e: (e.kind.value, e.normalized_name))
    ordered_facts = sorted(
        facts, key=lambda f: (str(f.scene_id), f.kind.value, f.value, str(f.fact_id))
    )
    ordered_links = sorted(links, key=lambda link: str(link.link_id))
    ordered_diagnostics = sorted(diagnostics, key=lambda d: (d.code, d.message))

    return ContinuityLedger(
        script_id=document.script_id,
        revision=document.revision,
        source_hash=document.source_hash,
        entities=ordered_entities,
        facts=ordered_facts,
        scene_contracts=scene_contracts,
        setup_payoff_links=ordered_links,
        diagnostics=ordered_diagnostics,
    )


def _link_setup_payoff(
    script_id: UUID,
    plant_facts: list[ContinuityFact],
    payoff_facts: list[ContinuityFact],
    scene_contracts: list[SceneContinuityContract],
) -> list[SetupPayoffLink]:
    links: list[SetupPayoffLink] = []
    used_payoffs: set[UUID] = set()
    ordinal = {contract.scene_id: contract.ordinal for contract in scene_contracts}
    for plant in plant_facts:
        for payoff in payoff_facts:
            if payoff.fact_id in used_payoffs:
                continue
            if plant.subject_entity_id != payoff.subject_entity_id:
                continue
            if plant.scene_id is None or payoff.scene_id is None:
                continue
            if ordinal[payoff.scene_id] < ordinal[plant.scene_id]:
                continue
            links.append(
                SetupPayoffLink(
                    link_id=stable_id("setup_payoff", script_id, plant.fact_id, payoff.fact_id),
                    entity_id=plant.subject_entity_id,
                    setup_fact_id=plant.fact_id,
                    payoff_fact_id=payoff.fact_id,
                    setup_scene_id=plant.scene_id,
                    payoff_scene_id=payoff.scene_id,
                )
            )
            used_payoffs.add(payoff.fact_id)
            break
    return links


def _drift_diagnostics(
    facts: list[ContinuityFact],
    entities: dict[tuple[EntityKind, str], Entity],
    scene_ordinals: dict[UUID, int],
) -> list[CompileDiagnostic]:
    """Emit typed warnings when prop/wardrobe/injury state changes across scenes."""
    by_id = {entity.entity_id: entity for entity in entities.values()}
    diagnostics: list[CompileDiagnostic] = []

    def ordered(entity_id: UUID, kinds: set[FactKind]) -> list[ContinuityFact]:
        selected = [
            fact
            for fact in facts
            if fact.subject_entity_id == entity_id
            and fact.kind in kinds
            and fact.scene_id is not None
        ]
        return sorted(
            selected,
            key=lambda fact: (
                scene_ordinals.get(fact.scene_id, 10**9) if fact.scene_id else 10**9,
                fact.value,
            ),
        )

    for entity in by_id.values():
        if entity.kind == EntityKind.PROP:
            timeline = ordered(entity.entity_id, {FactKind.HOLDS, FactKind.ABSENT})
            saw_present = False
            for fact in timeline:
                if fact.kind == FactKind.HOLDS:
                    saw_present = True
                elif fact.kind == FactKind.ABSENT and saw_present:
                    diagnostics.append(
                        CompileDiagnostic(
                            code="CL201",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                f"Prop state drift for '{entity.name}': previously present, "
                                f"later marked absent ({fact.value})."
                            ),
                            source_span=fact.source_span,
                        )
                    )
                    break

        if entity.kind == EntityKind.WARDROBE:
            states = [
                fact.value.split(":", 1)[-1]
                for fact in ordered(entity.entity_id, {FactKind.WEARS})
                if ":" in fact.value
            ]
            unique = list(dict.fromkeys(states))
            if len(unique) >= 2:
                first = next(
                    fact
                    for fact in ordered(entity.entity_id, {FactKind.WEARS})
                    if ":" in fact.value
                )
                diagnostics.append(
                    CompileDiagnostic(
                        code="CL202",
                        severity=DiagnosticSeverity.WARNING,
                        message=(
                            f"Wardrobe state drift for '{entity.name}': "
                            + " -> ".join(unique)
                            + "."
                        ),
                        source_span=first.source_span,
                    )
                )

        if entity.kind == EntityKind.INJURY:
            states = [
                fact.value.split(":", 1)[-1]
                for fact in ordered(entity.entity_id, {FactKind.INJURED})
                if ":" in fact.value
            ]
            unique = list(dict.fromkeys(states))
            if len(unique) >= 2:
                first = next(
                    fact
                    for fact in ordered(entity.entity_id, {FactKind.INJURED})
                    if ":" in fact.value
                )
                diagnostics.append(
                    CompileDiagnostic(
                        code="CL203",
                        severity=DiagnosticSeverity.INFO,
                        message=(
                            f"Injury progression for '{entity.name}': " + " -> ".join(unique) + "."
                        ),
                        source_span=first.source_span,
                    )
                )

    return diagnostics
