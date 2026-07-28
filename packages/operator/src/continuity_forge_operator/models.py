from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ApprovalStatus(StrEnum):
    REQUESTED = "requested"
    GRANTED = "granted"
    DENIED = "denied"


class MutationEnvelope(BaseModel):
    actor_id: Annotated[str, Field(min_length=1)]
    authorization_scope: Annotated[str, Field(min_length=1)]
    idempotency_key: Annotated[str, Field(min_length=1)]
    rationale: Annotated[str, Field(min_length=1)]
    command_schema_version: str = "m4.operator.v1"
    expected_state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None


class WriteLease(BaseModel):
    document_key: str
    holder: str
    scope: str
    acquired_at: datetime
    expires_at: datetime

    def is_active(self, now: datetime | None = None) -> bool:
        return (now or utc_now()) < self.expires_at


class ApprovalRecord(BaseModel):
    approval_id: UUID
    document_key: str
    kind: str
    status: ApprovalStatus
    actor_id: str
    rationale: str
    created_at: datetime
    target_ref: str | None = None


class ProjectRecord(BaseModel):
    document_key: str
    title: str
    source_text: str
    source_hash: str
    revision: str
    format: str
    updated_at: datetime
    production_ir: dict[str, Any] | None = None
    continuity_ledger: dict[str, Any] | None = None
    shot_contracts: dict[str, Any] | None = None
    last_pipeline_run_id: UUID | None = None
    state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None


def approval_id(document_key: str, kind: str, idempotency_key: str) -> UUID:
    return stable_id("approval", document_key, kind, idempotency_key)


def project_state_hash(project: ProjectRecord) -> str:
    return content_hash(f"{project.source_hash}|{project.revision}|{project.last_pipeline_run_id}")
