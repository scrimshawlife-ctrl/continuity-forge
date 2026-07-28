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
    """Universal write contract for Continuity Forge mutations.

    Every canon-writing path MUST accept or construct a ``MutationEnvelope``:

    - ``ProjectStore.ingest_script`` / approvals
    - REST ``/v1/projects/ingest``, ``/v1/approvals/*``
    - MCP ``ingest_script`` (and any future canon-writing tool)
    - Adapters that build ``PipelineCommand`` must carry the same identity,
      scope, idempotency, and rationale fields (pipeline uses its own
      ``command_schema_version``).

    Non-canon PROPOSED generation may include the same fields for audit
    but does not write film canon.

    ``expected_state_hash`` is the project's ``state_hash`` (from status /
    ``ProjectRecord``) when continuing prior project state. Pipeline-only
    optimistic concurrency uses prior ``shot_contracts_hash`` on
    ``PipelineCommand`` and is a separate domain.
    """

    actor_id: Annotated[str, Field(min_length=1)]
    authorization_scope: Annotated[str, Field(min_length=1)]
    idempotency_key: Annotated[str, Field(min_length=1)]
    rationale: Annotated[str, Field(min_length=1)]
    command_schema_version: str = "m4.operator.v1"
    expected_state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None

    @classmethod
    def from_parts(
        cls,
        *,
        actor_id: str,
        authorization_scope: str,
        idempotency_key: str,
        rationale: str,
        expected_state_hash: str | None = None,
        command_schema_version: str = "m4.operator.v1",
    ) -> MutationEnvelope:
        """Build and validate a write-contract envelope from free fields."""
        return cls(
            actor_id=actor_id,
            authorization_scope=authorization_scope,
            idempotency_key=idempotency_key,
            rationale=rationale,
            expected_state_hash=expected_state_hash,
            command_schema_version=command_schema_version,
        )


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
