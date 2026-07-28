from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id
from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStepName(StrEnum):
    COMPILE = "compile_screenplay"
    LEDGER = "build_continuity_ledger"
    SHOTS = "compile_shot_contracts"


class PipelineCommand(BaseModel):
    """Typed operator command for the kernel pipeline (mutation contract)."""

    actor_id: Annotated[str, Field(min_length=1)]
    authorization_scope: Annotated[str, Field(min_length=1)]
    idempotency_key: Annotated[str, Field(min_length=1)]
    command_schema_version: str = "m3.pipeline.v1"
    rationale: Annotated[str, Field(min_length=1)]
    expected_state_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None

    title: str = "Untitled"
    text: str
    revision: str = "0.1.0"
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"

    @model_validator(mode="after")
    def validate_command(self) -> PipelineCommand:
        if not self.text.strip():
            raise ValueError("pipeline command text must not be empty")
        if self.command_schema_version != "m3.pipeline.v1":
            raise ValueError("unsupported command schema version")
        return self

    def command_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"rationale"})
        return content_hash(repr(sorted(payload.items())))


class CheckpointRecord(BaseModel):
    step: PipelineStepName
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None = None
    output_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    detail: str | None = None


class PipelineArtifacts(BaseModel):
    production_ir: dict[str, Any]
    continuity_ledger: dict[str, Any]
    shot_contracts: dict[str, Any]
    production_ir_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    ledger_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    shot_contracts_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class WorkflowRun(BaseModel):
    run_id: UUID
    status: RunStatus
    command: PipelineCommand
    command_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    created_at: datetime
    updated_at: datetime
    checkpoints: list[CheckpointRecord] = Field(default_factory=list)
    artifacts: PipelineArtifacts | None = None
    error: str | None = None
    attempt: Annotated[int, Field(ge=1)] = 1
    workflow_type: str = "KernelPipelineWorkflow"
    runtime: str = "in_process"

    @property
    def idempotency_key(self) -> str:
        return self.command.idempotency_key


def new_run_id(command: PipelineCommand) -> UUID:
    return stable_id(
        "workflow_run",
        command.idempotency_key,
        command.command_schema_version,
        command.actor_id,
    )
