"""Deterministic shot-contract compiler from Production IR + continuity ledger."""

from __future__ import annotations

from uuid import UUID

from continuity_forge_ir import (
    AtomType,
    CompileDiagnostic,
    DiagnosticSeverity,
    ScriptDocument,
    content_hash,
    stable_id,
)
from continuity_forge_ledger import (
    ContinuityLedger,
    EntityKind,
    FactKind,
    build_continuity_ledger,
)

from .models import (
    ConstraintCode,
    ConstraintStrength,
    ShotConstraint,
    ShotContract,
    ShotContractBundle,
    ValidationCheck,
)

DEFAULT_CAPABILITIES = ("image", "video", "continuity_validation")


def compile_shot_contracts(
    document: ScriptDocument,
    ledger: ContinuityLedger | None = None,
) -> ShotContractBundle:
    """Compile one model-neutral shot contract per scene."""
    active_ledger = ledger or build_continuity_ledger(document)
    if active_ledger.script_id != document.script_id:
        raise ValueError("ledger script_id must match Production IR script_id")
    if active_ledger.source_hash != document.source_hash:
        raise ValueError("ledger source_hash must match Production IR source_hash")

    entity_by_id = {entity.entity_id: entity for entity in active_ledger.entities}
    contracts: list[ShotContract] = []
    diagnostics: list[CompileDiagnostic] = list(active_ledger.diagnostics)

    for scene in document.scenes:
        scene_facts = [fact for fact in active_ledger.facts if fact.scene_id == scene.scene_id]
        contract_row = next(
            (row for row in active_ledger.scene_contracts if row.scene_id == scene.scene_id),
            None,
        )
        required_atoms = [
            atom.atom_id
            for atom in scene.atoms
            if atom.required_on_screen or atom.type == AtomType.SCENE_HEADING
        ]
        if not required_atoms:
            required_atoms = [scene.atoms[0].atom_id]

        constraints: list[ShotConstraint] = []
        required_entities: set[UUID] = set()

        # Atom requirements.
        for atom in scene.atoms:
            if atom.atom_id not in required_atoms:
                continue
            constraints.append(
                ShotConstraint(
                    constraint_id=stable_id(
                        "constraint", document.script_id, scene.scene_id, "atom", atom.atom_id
                    ),
                    strength=ConstraintStrength.HARD,
                    code=ConstraintCode.REQUIRE_ATOM,
                    description=f"Include narrative atom ({atom.type.value}): {atom.text[:120]}",
                    atom_id=atom.atom_id,
                )
            )

        # Location.
        if contract_row and contract_row.location_entity_id is not None:
            location = entity_by_id[contract_row.location_entity_id]
            required_entities.add(location.entity_id)
            constraints.append(
                ShotConstraint(
                    constraint_id=stable_id(
                        "constraint",
                        document.script_id,
                        scene.scene_id,
                        "location",
                        location.entity_id,
                    ),
                    strength=ConstraintStrength.HARD,
                    code=ConstraintCode.REQUIRE_LOCATION,
                    description=f"Location must read as '{location.name}'.",
                    entity_id=location.entity_id,
                )
            )

        # Characters present.
        if contract_row:
            for entity_id in contract_row.characters_present:
                entity = entity_by_id[entity_id]
                required_entities.add(entity_id)
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "character",
                            entity_id,
                        ),
                        strength=ConstraintStrength.HARD,
                        code=ConstraintCode.REQUIRE_CHARACTER,
                        description=f"Character '{entity.name}' must be depictable/present.",
                        entity_id=entity_id,
                    )
                )

        # Props / wardrobe / injury from scene facts.
        for fact in scene_facts:
            entity = entity_by_id[fact.subject_entity_id]
            if fact.kind == FactKind.HOLDS and entity.kind == EntityKind.PROP:
                required_entities.add(entity.entity_id)
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "prop",
                            fact.fact_id,
                        ),
                        strength=ConstraintStrength.HARD,
                        code=ConstraintCode.REQUIRE_PROP,
                        description=f"Prop '{entity.name}' must be visible/accounted ({fact.value}).",
                        entity_id=entity.entity_id,
                        fact_ids=[fact.fact_id],
                    )
                )
            elif fact.kind == FactKind.ABSENT and entity.kind == EntityKind.PROP:
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "forbid_prop",
                            fact.fact_id,
                        ),
                        strength=ConstraintStrength.PROHIBITED,
                        code=ConstraintCode.FORBID_PROP,
                        description=f"Prop '{entity.name}' must not appear ({fact.value}).",
                        entity_id=entity.entity_id,
                        fact_ids=[fact.fact_id],
                    )
                )
            elif fact.kind == FactKind.WEARS and entity.kind == EntityKind.WARDROBE:
                required_entities.add(entity.entity_id)
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "wardrobe",
                            fact.fact_id,
                        ),
                        strength=ConstraintStrength.HARD,
                        code=ConstraintCode.REQUIRE_WARDROBE_STATE,
                        description=f"Wardrobe '{entity.name}' state: {fact.value}.",
                        entity_id=entity.entity_id,
                        fact_ids=[fact.fact_id],
                    )
                )
            elif fact.kind == FactKind.INJURED and entity.kind == EntityKind.INJURY:
                required_entities.add(entity.entity_id)
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "injury",
                            fact.fact_id,
                        ),
                        strength=ConstraintStrength.HARD,
                        code=ConstraintCode.REQUIRE_INJURY_STATE,
                        description=f"Injury continuity for '{entity.name}': {fact.value}.",
                        entity_id=entity.entity_id,
                        fact_ids=[fact.fact_id],
                    )
                )
            elif fact.kind in {FactKind.PLANTS, FactKind.PAYS_OFF}:
                constraints.append(
                    ShotConstraint(
                        constraint_id=stable_id(
                            "constraint",
                            document.script_id,
                            scene.scene_id,
                            "creative",
                            fact.fact_id,
                        ),
                        strength=ConstraintStrength.SOFT,
                        code=ConstraintCode.CREATIVE_TARGET,
                        description=f"{fact.kind.value}: {fact.value[:160]}",
                        entity_id=entity.entity_id,
                        fact_ids=[fact.fact_id],
                    )
                )

        state_payload = "|".join(
            sorted(
                f"{fact.kind.value}:{fact.subject_entity_id}:{_norm(fact.value)}"
                for fact in scene_facts
            )
        )
        start_state_hash = content_hash(f"start|{scene.scene_id}|{state_payload}")
        end_state_hash = content_hash(f"end|{scene.scene_id}|{state_payload}")

        validation_checks = [
            ValidationCheck(
                check_id="atoms_present",
                description="All required narrative atoms are represented in the render.",
            ),
            ValidationCheck(
                check_id="hard_constraints",
                description="All hard continuity constraints evaluate true.",
            ),
            ValidationCheck(
                check_id="prohibitions",
                description="No prohibited props or mutations appear.",
            ),
            ValidationCheck(
                check_id="state_hash",
                description="End-state hash matches expected continuity state.",
            ),
        ]

        contracts.append(
            ShotContract(
                shot_id=stable_id("shot", document.script_id, scene.scene_id, 1),
                scene_id=scene.scene_id,
                scene_ordinal=scene.ordinal,
                shot_ordinal=1,
                slugline=scene.slugline,
                label=f"scene-{scene.ordinal:03d}-master",
                required_atom_ids=required_atoms,
                constraints=constraints,
                required_entity_ids=sorted(required_entities, key=str),
                start_state_hash=start_state_hash,
                end_state_hash=end_state_hash,
                provider_capabilities=list(DEFAULT_CAPABILITIES),
                validation_checks=validation_checks,
            )
        )

    if not contracts:
        diagnostics.append(
            CompileDiagnostic(
                code="SC100",
                severity=DiagnosticSeverity.ERROR,
                message="No shot contracts could be compiled because the document has no scenes.",
            )
        )

    ledger_hash = content_hash(active_ledger.model_dump_json(exclude={"diagnostics"}))
    return ShotContractBundle(
        script_id=document.script_id,
        revision=document.revision,
        source_hash=document.source_hash,
        ledger_hash=ledger_hash,
        contracts=contracts,
        diagnostics=diagnostics,
    )


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())
