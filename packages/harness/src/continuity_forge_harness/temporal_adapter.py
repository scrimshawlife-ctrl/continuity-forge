"""Temporal adapter contracts for the kernel pipeline.

M3 does not require a running Temporal cluster. These definitions document the
stable workflow/activity surface that a Temporal worker will host in later work.
"""

from __future__ import annotations

from typing import Any, Final

from .models import PipelineCommand, PipelineStepName

WORKFLOW_TYPE: Final[str] = "KernelPipelineWorkflow"
TASK_QUEUE: Final[str] = "continuity-forge-kernel"
ACTIVITY_NAMES: Final[tuple[str, ...]] = tuple(step.value for step in PipelineStepName)


def workflow_id_for(command: PipelineCommand) -> str:
    """Deterministic Temporal workflow ID from the idempotency key."""
    return f"kernel-pipeline:{command.idempotency_key}"


def activity_payload(command: PipelineCommand) -> dict[str, Any]:
    """JSON-serializable activity input shared by compile/ledger/shots steps."""
    return command.model_dump(mode="json")


def temporal_registration_manifest() -> dict[str, Any]:
    """Machine-readable adapter contract for worker bootstrapping."""
    return {
        "workflow_type": WORKFLOW_TYPE,
        "task_queue": TASK_QUEUE,
        "activities": list(ACTIVITY_NAMES),
        "command_schema_version": "m3.pipeline.v1",
        "notes": [
            "Activities must call continuity_forge_harness.pipeline step functions only.",
            "Workflow run records are execution provenance, never canonical film state.",
            "Idempotency is owned by PipelineCommand.idempotency_key / workflow_id_for().",
        ],
    }
