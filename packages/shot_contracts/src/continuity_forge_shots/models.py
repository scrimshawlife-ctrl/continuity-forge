from __future__ import annotations

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from continuity_forge_ir import CompileDiagnostic
from pydantic import BaseModel, Field, model_validator


class ConstraintStrength(StrEnum):
    HARD = "hard"
    SOFT = "soft"
    PROHIBITED = "prohibited"


class ConstraintCode(StrEnum):
    REQUIRE_ATOM = "require_atom"
    REQUIRE_CHARACTER = "require_character"
    REQUIRE_PROP = "require_prop"
    REQUIRE_WARDROBE_STATE = "require_wardrobe_state"
    REQUIRE_INJURY_STATE = "require_injury_state"
    REQUIRE_LOCATION = "require_location"
    FORBID_PROP = "forbid_prop"
    FORBID_MUTATION = "forbid_mutation"
    CREATIVE_TARGET = "creative_target"


class ShotConstraint(BaseModel):
    constraint_id: UUID
    strength: ConstraintStrength
    code: ConstraintCode
    description: str
    entity_id: UUID | None = None
    atom_id: UUID | None = None
    fact_ids: list[UUID] = Field(default_factory=list)


class ValidationCheck(BaseModel):
    check_id: str
    description: str


class ShotContract(BaseModel):
    shot_id: UUID
    scene_id: UUID
    scene_ordinal: Annotated[int, Field(ge=1)]
    shot_ordinal: Annotated[int, Field(ge=1)]
    slugline: str
    label: str
    required_atom_ids: list[UUID]
    constraints: list[ShotConstraint]
    required_entity_ids: list[UUID] = Field(default_factory=list)
    start_state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    end_state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    provider_capabilities: list[str] = Field(default_factory=list)
    validation_checks: list[ValidationCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shot(self) -> ShotContract:
        if not self.required_atom_ids:
            raise ValueError("shot contracts require at least one narrative atom")
        if len(set(self.required_atom_ids)) != len(self.required_atom_ids):
            raise ValueError("required atom IDs must be unique")
        constraint_ids = [item.constraint_id for item in self.constraints]
        if len(set(constraint_ids)) != len(constraint_ids):
            raise ValueError("constraint IDs must be unique within a shot")
        return self


class ShotContractBundle(BaseModel):
    script_id: UUID
    revision: str
    source_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    ledger_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    contracts: list[ShotContract]
    diagnostics: list[CompileDiagnostic] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bundle(self) -> ShotContractBundle:
        shot_ids = [contract.shot_id for contract in self.contracts]
        if len(set(shot_ids)) != len(shot_ids):
            raise ValueError("shot IDs must be unique")
        scene_ids = [contract.scene_id for contract in self.contracts]
        if len(set(scene_ids)) != len(scene_ids):
            raise ValueError("M2 requires exactly one contract per scene")
        return self
