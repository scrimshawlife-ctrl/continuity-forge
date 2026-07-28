from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from continuity_forge_ir import CompileDiagnostic, SourceSpan
from pydantic import BaseModel, Field, model_validator


class EntityKind(StrEnum):
    CHARACTER = "character"
    LOCATION = "location"
    PROP = "prop"
    WARDROBE = "wardrobe"
    INJURY = "injury"


class FactKind(StrEnum):
    APPEARS_IN = "appears_in"
    ENTERS = "enters"
    EXITS = "exits"
    HOLDS = "holds"
    WEARS = "wears"
    INJURED = "injured"
    PLANTS = "plants"
    PAYS_OFF = "pays_off"
    STATE = "state"
    ABSENT = "absent"


class EvidenceGrade(StrEnum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"


class Entity(BaseModel):
    entity_id: UUID
    kind: EntityKind
    name: str
    normalized_name: str
    first_scene_id: UUID | None = None
    aliases: list[str] = Field(default_factory=list)


class ContinuityFact(BaseModel):
    fact_id: UUID
    kind: FactKind
    subject_entity_id: UUID
    object_entity_id: UUID | None = None
    scene_id: UUID | None
    atom_ids: list[UUID] = Field(default_factory=list)
    value: str
    evidence: EvidenceGrade
    source_span: SourceSpan | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> ContinuityFact:
        if not self.atom_ids:
            raise ValueError("continuity facts require at least one atom provenance reference")
        return self


class SceneContinuityContract(BaseModel):
    scene_id: UUID
    ordinal: Annotated[int, Field(ge=1)]
    slugline: str
    location_entity_id: UUID | None
    characters_present: list[UUID] = Field(default_factory=list)
    entries: list[UUID] = Field(default_factory=list)
    exits: list[UUID] = Field(default_factory=list)
    props_referenced: list[UUID] = Field(default_factory=list)
    wardrobe_referenced: list[UUID] = Field(default_factory=list)
    injuries_referenced: list[UUID] = Field(default_factory=list)
    fact_ids: list[UUID] = Field(default_factory=list)


class SetupPayoffLink(BaseModel):
    link_id: UUID
    entity_id: UUID
    setup_fact_id: UUID
    payoff_fact_id: UUID
    setup_scene_id: UUID
    payoff_scene_id: UUID


class ContinuityLedger(BaseModel):
    script_id: UUID
    revision: str
    source_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    entities: list[Entity]
    facts: list[ContinuityFact]
    scene_contracts: list[SceneContinuityContract]
    setup_payoff_links: list[SetupPayoffLink] = Field(default_factory=list)
    diagnostics: list[CompileDiagnostic] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ledger(self) -> ContinuityLedger:
        entity_ids = {entity.entity_id for entity in self.entities}
        if len(entity_ids) != len(self.entities):
            raise ValueError("entity IDs must be unique")
        fact_ids = {fact.fact_id for fact in self.facts}
        if len(fact_ids) != len(self.facts):
            raise ValueError("fact IDs must be unique")
        for fact in self.facts:
            if fact.subject_entity_id not in entity_ids:
                raise ValueError("facts must reference known subject entities")
            if fact.object_entity_id is not None and fact.object_entity_id not in entity_ids:
                raise ValueError("facts must reference known object entities")
        for contract in self.scene_contracts:
            for entity_id in (
                *contract.characters_present,
                *contract.entries,
                *contract.exits,
                *contract.props_referenced,
                *contract.wardrobe_referenced,
                *contract.injuries_referenced,
            ):
                if entity_id not in entity_ids:
                    raise ValueError("scene contracts must reference known entities")
            if (
                contract.location_entity_id is not None
                and contract.location_entity_id not in entity_ids
            ):
                raise ValueError("scene location must reference a known entity")
            for fact_id in contract.fact_ids:
                if fact_id not in fact_ids:
                    raise ValueError("scene contracts must reference known facts")
        for link in self.setup_payoff_links:
            if link.entity_id not in entity_ids:
                raise ValueError("setup/payoff links must reference known entities")
            if link.setup_fact_id not in fact_ids or link.payoff_fact_id not in fact_ids:
                raise ValueError("setup/payoff links must reference known facts")
        return self
