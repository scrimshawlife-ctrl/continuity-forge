"""Ordered workflow events for operator progress (observability only).

Derived from ``WorkflowRun`` checkpoints for poll/resume. Never owns film canon.
Payloads carry hashes and labels only — no provider secrets or API keys.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id
from pydantic import BaseModel, Field

from .models import (
    CheckpointRecord,
    PipelineStepName,
    RunStatus,
    WorkflowRun,
    utc_now,
)

# Kernel pipeline step order for percent/step progress.
KERNEL_STEPS: tuple[PipelineStepName, ...] = (
    PipelineStepName.COMPILE,
    PipelineStepName.LEDGER,
    PipelineStepName.SHOTS,
)

_SECRET_PATTERNS = re.compile(
    r"(?i)(api[_-]?key|authorization|bearer\s+\S+|secret|password)\s*[:=]\s*\S+"
)


class WorkflowEventKind(StrEnum):
    RUN_STARTED = "run_started"
    CHECKPOINT = "checkpoint"
    PROVIDER_ATTEMPT = "provider_attempt"
    VALIDATION = "validation"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class WorkflowEvent(BaseModel):
    """One ordered observability event for a workflow run."""

    event_id: str
    sequence: int
    run_id: str
    kind: WorkflowEventKind
    timestamp: datetime
    step: str | None = None
    label: str | None = None
    status: str | None = None
    # Non-canon payload refs only (hashes, codes) — never full IR or secrets.
    payload_ref: dict[str, Any] = Field(default_factory=dict)
    claim: str = "workflow_event_observability_not_canon"


class WorkflowProgress(BaseModel):
    """Step / percent view for UI without implying production readiness."""

    current_step: str | None = None
    current_label: str | None = None
    completed_steps: int = 0
    total_steps: int = len(KERNEL_STEPS)
    percent: int = 0
    run_status: str
    last_successful_checkpoint: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    workflow_complete_is_not_production_ready: bool = True
    note: str = (
        "Workflow progress is run provenance only. "
        "Workflow complete does not mean production ready."
    )


class WorkflowEventPage(BaseModel):
    """Poll response: events after a cursor + progress snapshot."""

    run_id: str
    status: str
    claim: str = "workflow_events_observability_not_canon"
    transport: str = "poll"
    workflow_complete_is_not_production_ready: bool = True
    events: list[WorkflowEvent] = Field(default_factory=list)
    progress: WorkflowProgress
    next_after_sequence: int = 0
    last_event_id: str | None = None


def redact_error(message: str | None) -> str | None:
    """Strip secret-like substrings from error text before streaming."""
    if message is None:
        return None
    return _SECRET_PATTERNS.sub("[redacted]", message)


def _step_label(step: PipelineStepName | str) -> str:
    value = step.value if isinstance(step, PipelineStepName) else str(step)
    return value.replace("_", " ")


def _event_id(run_id: UUID | str, sequence: int, kind: str, step: str | None) -> str:
    return str(stable_id("wf_event", str(run_id), sequence, kind, step or ""))


def events_from_workflow_run(run: WorkflowRun) -> list[WorkflowEvent]:
    """Build a deterministic ordered event list from a stored run.

    Same run always yields the same event_ids and order (idempotent replay).
    """
    events: list[WorkflowEvent] = []
    seq = 0

    def add(
        kind: WorkflowEventKind,
        *,
        timestamp: datetime,
        step: str | None = None,
        label: str | None = None,
        status: str | None = None,
        payload_ref: dict[str, Any] | None = None,
    ) -> None:
        nonlocal seq
        seq += 1
        events.append(
            WorkflowEvent(
                event_id=_event_id(run.run_id, seq, kind.value, step),
                sequence=seq,
                run_id=str(run.run_id),
                kind=kind,
                timestamp=timestamp,
                step=step,
                label=label,
                status=status,
                payload_ref=payload_ref or {},
            )
        )

    add(
        WorkflowEventKind.RUN_STARTED,
        timestamp=run.created_at,
        status=RunStatus.RUNNING.value,
        payload_ref={
            "workflow_type": run.workflow_type,
            "attempt": run.attempt,
            "command_hash": run.command_hash,
            # Never include command.text or credentials.
            "document_key": run.command.document_key,
            "idempotency_key": run.command.idempotency_key,
        },
    )

    for cp in run.checkpoints:
        step_name = cp.step.value if isinstance(cp.step, PipelineStepName) else str(cp.step)
        add(
            WorkflowEventKind.CHECKPOINT,
            timestamp=cp.completed_at or cp.started_at,
            step=step_name,
            label=_step_label(cp.step),
            status=cp.status.value if isinstance(cp.status, RunStatus) else str(cp.status),
            payload_ref={
                "output_hash": cp.output_hash,
                "detail": cp.detail,
            },
        )

    if run.status == RunStatus.COMPLETED:
        add(
            WorkflowEventKind.RUN_COMPLETED,
            timestamp=run.updated_at,
            status=RunStatus.COMPLETED.value,
            payload_ref={
                "production_ir_hash": (run.artifacts.production_ir_hash if run.artifacts else None),
                "ledger_hash": run.artifacts.ledger_hash if run.artifacts else None,
                "shot_contracts_hash": (
                    run.artifacts.shot_contracts_hash if run.artifacts else None
                ),
            },
        )
    elif run.status == RunStatus.FAILED:
        add(
            WorkflowEventKind.RUN_FAILED,
            timestamp=run.updated_at,
            status=RunStatus.FAILED.value,
            payload_ref={
                "error_code": "pipeline_failed",
                "error_message": redact_error(run.error),
                "last_successful_checkpoint": _last_successful_step(run.checkpoints),
            },
        )

    return events


def _last_successful_step(checkpoints: list[CheckpointRecord]) -> str | None:
    for cp in reversed(checkpoints):
        status = cp.status.value if isinstance(cp.status, RunStatus) else str(cp.status)
        if status == RunStatus.COMPLETED.value:
            step = cp.step.value if isinstance(cp.step, PipelineStepName) else str(cp.step)
            return step
    return None


def progress_from_run(run: WorkflowRun) -> WorkflowProgress:
    """Compute step/percent progress from run checkpoints + status."""
    completed = 0
    last_ok: str | None = None
    for cp in run.checkpoints:
        status = cp.status.value if isinstance(cp.status, RunStatus) else str(cp.status)
        if status == RunStatus.COMPLETED.value:
            completed += 1
            last_ok = cp.step.value if isinstance(cp.step, PipelineStepName) else str(cp.step)

    total = len(KERNEL_STEPS)
    current: str | None
    if run.status == RunStatus.COMPLETED:
        percent = 100
        current = last_ok or KERNEL_STEPS[-1].value
    elif run.status == RunStatus.FAILED:
        percent = min(99, int(100 * completed / total) if total else 0)
        current = last_ok
    else:
        percent = min(99, int(100 * completed / total) if total else 0)
        # Next expected step
        if completed < total:
            current = KERNEL_STEPS[completed].value
        else:
            current = last_ok

    error_code = None
    error_message = None
    if run.status == RunStatus.FAILED:
        error_code = "pipeline_failed"
        error_message = redact_error(run.error)

    return WorkflowProgress(
        current_step=current,
        current_label=_step_label(current) if current else None,
        completed_steps=completed if run.status != RunStatus.COMPLETED else total,
        total_steps=total,
        percent=percent,
        run_status=run.status.value if isinstance(run.status, RunStatus) else str(run.status),
        last_successful_checkpoint=last_ok,
        error_code=error_code,
        error_message=error_message,
    )


def filter_events_after(
    events: list[WorkflowEvent],
    *,
    after_sequence: int = 0,
    last_event_id: str | None = None,
) -> list[WorkflowEvent]:
    """Resume cursor: return events strictly after sequence or last_event_id."""
    if last_event_id:
        idx = next((i for i, e in enumerate(events) if e.event_id == last_event_id), None)
        if idx is not None:
            return events[idx + 1 :]
        # Unknown id: fall through to sequence cursor
    if after_sequence > 0:
        return [e for e in events if e.sequence > after_sequence]
    return list(events)


def build_event_page(
    run: WorkflowRun,
    *,
    after_sequence: int = 0,
    last_event_id: str | None = None,
) -> WorkflowEventPage:
    """Poll-first transport page for a run."""
    all_events = events_from_workflow_run(run)
    page_events = filter_events_after(
        all_events,
        after_sequence=after_sequence,
        last_event_id=last_event_id,
    )
    last_id = all_events[-1].event_id if all_events else None
    next_seq = all_events[-1].sequence if all_events else 0
    return WorkflowEventPage(
        run_id=str(run.run_id),
        status=run.status.value if isinstance(run.status, RunStatus) else str(run.status),
        events=page_events,
        progress=progress_from_run(run),
        next_after_sequence=next_seq,
        last_event_id=last_id,
    )


def events_from_cost_traces(
    *,
    run_id: str,
    cost_events: list[Any],
    base_sequence: int = 0,
    started_at: datetime | None = None,
) -> list[WorkflowEvent]:
    """Optional: map cost/provider traces into provider_attempt events (proof runs).

    ``cost_events`` are CostEvent-like objects with provider_id, model, seed, etc.
    Secrets are never copied (only ids/hashes).
    """
    ts = started_at or utc_now()
    out: list[WorkflowEvent] = []
    seq = base_sequence
    for item in cost_events:
        if hasattr(item, "model_dump"):
            data = item.model_dump(mode="json")
        elif isinstance(item, dict):
            data = item
        else:
            continue
        seq += 1
        kind = WorkflowEventKind.PROVIDER_ATTEMPT
        if data.get("kind") == "validate":
            kind = WorkflowEventKind.VALIDATION
        payload = {
            "provider_id": data.get("provider_id"),
            "model": data.get("model"),
            "seed": data.get("seed"),
            "latency_ms": data.get("latency_ms"),
            "estimated_cost": data.get("estimated_cost"),
            "authority": data.get("authority", "PROPOSED"),
            "candidate_hash": data.get("candidate_hash"),
            "shot_id": data.get("shot_id"),
            "attempt": data.get("attempt"),
            "is_retry": data.get("is_retry"),
        }
        # Drop anything that looks like a secret key name
        for bad in list(payload):
            if re.search(r"(?i)(api_key|secret|password|authorization)", bad):
                del payload[bad]
        out.append(
            WorkflowEvent(
                event_id=_event_id(run_id, seq, kind.value, str(data.get("shot_id") or "")),
                sequence=seq,
                run_id=str(run_id),
                kind=kind,
                timestamp=ts,
                step=str(data.get("shot_id") or "")[:36] or None,
                label=f"provider {payload.get('provider_id') or 'unknown'}",
                status="PROPOSED",
                payload_ref=payload,
            )
        )
    return out


def stream_fingerprint(events: list[WorkflowEvent]) -> str:
    """Stable hash of event_id sequence for replay equality tests."""
    return content_hash("|".join(e.event_id for e in events))
