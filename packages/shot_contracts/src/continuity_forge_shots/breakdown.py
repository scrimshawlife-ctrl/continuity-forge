"""Machine-readable shot-by-shot breakdown with continuity (handoff export).

Paste/import screenplay → compile → ledger → shot contracts → one package
for operators, connectors, and offline export. Read-side only; no media;
does not elevate PROPOSED candidates to canon.
"""

from __future__ import annotations

from typing import Any, Literal

from continuity_forge_ir import ScriptDocument, content_hash
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from pydantic import BaseModel, Field

from .compiler import compile_shot_contracts
from .models import ShotContractBundle

BREAKDOWN_SCHEMA = "cf.breakdown.v1"
BREAKDOWN_CLAIM = "shot_breakdown_with_continuity_not_production_film"


class EntitySummary(BaseModel):
    entity_id: str
    kind: str
    name: str


class SetupPayoffSummary(BaseModel):
    link_id: str
    entity_id: str
    entity_name: str | None = None
    setup_scene_id: str
    payoff_scene_id: str


class SceneSummary(BaseModel):
    scene_id: str
    ordinal: int
    slugline: str
    atom_count: int
    characters: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    location: str | None = None


class ShotBreakdownRow(BaseModel):
    """One shot in connector-friendly form."""

    shot_id: str
    scene_id: str
    scene_ordinal: int
    shot_ordinal: int
    slugline: str
    label: str
    required_entity_names: list[str] = Field(default_factory=list)
    required_entity_ids: list[str] = Field(default_factory=list)
    constraints: list[dict[str, Any]] = Field(default_factory=list)
    start_state_hash: str
    end_state_hash: str
    provider_capabilities: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    # Continuity context for this scene/shot
    characters_present: list[str] = Field(default_factory=list)
    props_referenced: list[str] = Field(default_factory=list)
    setup_payoff_entity_names: list[str] = Field(default_factory=list)


class BreakdownPackage(BaseModel):
    """Handoff package: scenes, continuity, shot-by-shot rows, provenance hashes."""

    schema_version: str = BREAKDOWN_SCHEMA
    claim: str = BREAKDOWN_CLAIM
    title: str
    document_key: str | None = None
    format: str = "fountain"
    revision: str = "0.1.0"
    source_hash: str
    production_ir_hash: str
    ledger_hash: str
    shot_contracts_hash: str
    package_hash: str = ""
    scene_count: int = 0
    shot_count: int = 0
    entity_count: int = 0
    scenes: list[SceneSummary] = Field(default_factory=list)
    entities: list[EntitySummary] = Field(default_factory=list)
    setup_payoff_links: list[SetupPayoffSummary] = Field(default_factory=list)
    shots: list[ShotBreakdownRow] = Field(default_factory=list)
    diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    authority_note: str = (
        "Shot breakdown and continuity are deterministic kernel outputs. "
        "Not production film. Provider media remains PROPOSED until approved."
    )


def _entity_name_map(ledger: ContinuityLedger) -> dict[str, str]:
    return {str(e.entity_id): e.name for e in ledger.entities}


def build_breakdown(
    document: ScriptDocument,
    *,
    ledger: ContinuityLedger | None = None,
    bundle: ShotContractBundle | None = None,
    title: str | None = None,
    document_key: str | None = None,
) -> BreakdownPackage:
    """Assemble breakdown from already-compiled IR (+ optional prebuilt ledger/shots)."""
    active_ledger = ledger or build_continuity_ledger(document)
    active_bundle = bundle or compile_shot_contracts(document, ledger=active_ledger)
    names = _entity_name_map(active_ledger)

    scene_contract_by_id = {str(sc.scene_id): sc for sc in active_ledger.scene_contracts}

    scenes: list[SceneSummary] = []
    for scene in document.scenes:
        sc = scene_contract_by_id.get(str(scene.scene_id))
        chars = [names.get(str(eid), str(eid)) for eid in sc.characters_present] if sc else []
        props = [names.get(str(eid), str(eid)) for eid in sc.props_referenced] if sc else []
        loc = None
        if sc and sc.location_entity_id is not None:
            loc = names.get(str(sc.location_entity_id))
        scenes.append(
            SceneSummary(
                scene_id=str(scene.scene_id),
                ordinal=scene.ordinal,
                slugline=scene.slugline,
                atom_count=len(scene.atoms),
                characters=chars,
                props=props,
                location=loc,
            )
        )

    entities = [
        EntitySummary(entity_id=str(e.entity_id), kind=e.kind.value, name=e.name)
        for e in active_ledger.entities
    ]

    setup_links = [
        SetupPayoffSummary(
            link_id=str(link.link_id),
            entity_id=str(link.entity_id),
            entity_name=names.get(str(link.entity_id)),
            setup_scene_id=str(link.setup_scene_id),
            payoff_scene_id=str(link.payoff_scene_id),
        )
        for link in active_ledger.setup_payoff_links
    ]

    # Entity names involved in setup/payoff per scene
    setup_by_scene: dict[str, set[str]] = {}
    for link in active_ledger.setup_payoff_links:
        ename = names.get(str(link.entity_id), str(link.entity_id))
        for sid in (str(link.setup_scene_id), str(link.payoff_scene_id)):
            setup_by_scene.setdefault(sid, set()).add(ename)

    shots: list[ShotBreakdownRow] = []
    for contract in active_bundle.contracts:
        sid = str(contract.scene_id)
        sc = scene_contract_by_id.get(sid)
        shot_chars = [names.get(str(eid), str(eid)) for eid in sc.characters_present] if sc else []
        shot_props = [names.get(str(eid), str(eid)) for eid in sc.props_referenced] if sc else []
        req_names = [names.get(str(eid), str(eid)) for eid in contract.required_entity_ids]
        shots.append(
            ShotBreakdownRow(
                shot_id=str(contract.shot_id),
                scene_id=sid,
                scene_ordinal=contract.scene_ordinal,
                shot_ordinal=contract.shot_ordinal,
                slugline=contract.slugline,
                label=contract.label,
                required_entity_names=req_names,
                required_entity_ids=[str(e) for e in contract.required_entity_ids],
                constraints=[
                    {
                        "code": c.code.value,
                        "strength": c.strength.value,
                        "description": c.description,
                        "entity_id": str(c.entity_id) if c.entity_id else None,
                        "entity_name": (names.get(str(c.entity_id)) if c.entity_id else None),
                    }
                    for c in contract.constraints
                ],
                start_state_hash=contract.start_state_hash,
                end_state_hash=contract.end_state_hash,
                provider_capabilities=list(contract.provider_capabilities),
                validation_checks=[v.check_id for v in contract.validation_checks],
                characters_present=shot_chars,
                props_referenced=shot_props,
                setup_payoff_entity_names=sorted(setup_by_scene.get(sid, set())),
            )
        )

    # Sort shots by scene then shot ordinal (deterministic)
    shots.sort(key=lambda r: (r.scene_ordinal, r.shot_ordinal, r.shot_id))

    ir_hash = content_hash(document.model_dump_json())
    ledger_hash = content_hash(active_ledger.model_dump_json(exclude={"diagnostics"}))
    shots_hash = content_hash(active_bundle.model_dump_json(exclude={"diagnostics"}))

    diagnostics: list[dict[str, Any]] = []
    for d in document.diagnostics:
        diagnostics.append(d.model_dump(mode="json"))
    for d in active_ledger.diagnostics:
        diagnostics.append(d.model_dump(mode="json"))
    for d in active_bundle.diagnostics:
        diagnostics.append(d.model_dump(mode="json"))

    pkg = BreakdownPackage(
        title=title or document.title,
        document_key=document_key,
        format=str(document.format),
        revision=document.revision,
        source_hash=document.source_hash,
        production_ir_hash=ir_hash,
        ledger_hash=ledger_hash,
        shot_contracts_hash=shots_hash,
        scene_count=len(scenes),
        shot_count=len(shots),
        entity_count=len(entities),
        scenes=scenes,
        entities=entities,
        setup_payoff_links=setup_links,
        shots=shots,
        diagnostics=diagnostics,
        package_hash="",
    )
    pkg = pkg.model_copy(
        update={"package_hash": content_hash(pkg.model_dump_json(exclude={"package_hash"}))}
    )
    return pkg


def build_breakdown_from_text(
    text: str,
    *,
    title: str = "Untitled",
    document_key: str | None = None,
    format: Literal["fountain", "fdx"] = "fountain",
    revision: str = "0.1.0",
) -> BreakdownPackage:
    """End-to-end: paste/import source → breakdown package (read-side)."""
    # Lazy import avoids circular import (compiler.incremental → shots).
    from continuity_forge_compiler import compile_fdx_text, compile_text

    compiler = compile_fdx_text if format == "fdx" else compile_text
    document = compiler(
        text,
        title=title,
        revision=revision,
        document_key=document_key,
    )
    return build_breakdown(
        document,
        title=title,
        document_key=document_key,
    )


def breakdown_to_markdown(package: BreakdownPackage) -> str:
    """Human-readable text export of the same package (not production film)."""
    lines: list[str] = [
        f"# {package.title}",
        "",
        f"_Claim: `{package.claim}`_",
        f"_Schema: `{package.schema_version}` · package_hash `{package.package_hash[:16]}…`_",
        "",
        f"- Scenes: **{package.scene_count}**",
        f"- Shots: **{package.shot_count}**",
        f"- Continuity entities: **{package.entity_count}**",
        f"- Setup/payoff links: **{len(package.setup_payoff_links)}**",
        "",
        "## Continuity entities",
        "",
    ]
    if not package.entities:
        lines.append("_None extracted._")
    else:
        for e in package.entities:
            lines.append(f"- **{e.name}** (`{e.kind}`) · `{e.entity_id[:8]}…`")
    lines.extend(["", "## Setup / payoff", ""])
    if not package.setup_payoff_links:
        lines.append("_None._")
    else:
        for link in package.setup_payoff_links:
            label = link.entity_name or link.entity_id[:8]
            lines.append(
                f"- **{label}**: setup scene `{link.setup_scene_id[:8]}…` → "
                f"payoff `{link.payoff_scene_id[:8]}…`"
            )
    lines.extend(["", "## Shot-by-shot breakdown", ""])
    for shot in package.shots:
        lines.append(f"### Shot {shot.scene_ordinal}.{shot.shot_ordinal} — {shot.slugline}")
        lines.append(f"- Label: `{shot.label}`")
        lines.append(f"- Shot ID: `{shot.shot_id}`")
        if shot.required_entity_names:
            lines.append(f"- Required: {', '.join(shot.required_entity_names)}")
        if shot.characters_present:
            lines.append(f"- Characters: {', '.join(shot.characters_present)}")
        if shot.props_referenced:
            lines.append(f"- Props: {', '.join(shot.props_referenced)}")
        if shot.setup_payoff_entity_names:
            lines.append(f"- Setup/payoff: {', '.join(shot.setup_payoff_entity_names)}")
        if shot.constraints:
            lines.append("- Constraints:")
            for c in shot.constraints:
                en = c.get("entity_name") or ""
                lines.append(
                    f"  - [{c.get('strength')}] {c.get('code')}: {c.get('description')}"
                    + (f" ({en})" if en else "")
                )
        lines.append("")
    lines.extend(
        [
            "---",
            package.authority_note,
            "",
        ]
    )
    return "\n".join(lines)
