"""Checkpointed kernel pipeline executor."""

from __future__ import annotations

from continuity_forge_compiler import compile_fdx_text, compile_text
from continuity_forge_ir import ScriptDocument, content_hash
from continuity_forge_ledger import build_continuity_ledger
from continuity_forge_shots import compile_shot_contracts

from .models import (
    CheckpointRecord,
    PipelineArtifacts,
    PipelineCommand,
    PipelineStepName,
    RunStatus,
    WorkflowRun,
    new_run_id,
    utc_now,
)
from .store import DEFAULT_RUN_STORE, RunStore


class PipelineError(RuntimeError):
    """Raised when a pipeline step fails."""


def execute_kernel_pipeline(
    command: PipelineCommand,
    *,
    store: RunStore | None = None,
) -> WorkflowRun:
    """Run compile → ledger → shot contracts with durable checkpoints and idempotency."""
    active_store = store or DEFAULT_RUN_STORE
    existing = active_store.get_by_idempotency(command.idempotency_key)
    command_hash = command.command_hash()
    if existing is not None:
        if existing.command_hash != command_hash:
            raise PipelineError("idempotency key reused with a different command payload")
        if existing.status == RunStatus.COMPLETED:
            return existing
        if existing.status in {RunStatus.RUNNING, RunStatus.PENDING}:
            return existing

    if existing is not None and existing.status == RunStatus.FAILED:
        run = existing.model_copy(
            update={
                "status": RunStatus.RUNNING,
                "updated_at": utc_now(),
                "attempt": existing.attempt + 1,
                "error": None,
                "checkpoints": [],
                "artifacts": None,
            }
        )
    else:
        now = utc_now()
        run = WorkflowRun(
            run_id=new_run_id(command),
            status=RunStatus.RUNNING,
            command=command,
            command_hash=command_hash,
            created_at=now,
            updated_at=now,
            attempt=1,
        )
    active_store.put(run)

    try:
        # Optional optimistic concurrency against prior kernel state.
        if command.expected_state_hash is not None:
            # First run has no prior state; expected hash is advisory metadata only in M3
            # unless a completed run exists for the same document_key.
            prior = _latest_completed_for_document(active_store, command)
            if (
                prior is not None
                and prior.artifacts is not None
                and prior.artifacts.shot_contracts_hash != command.expected_state_hash
            ):
                raise PipelineError(
                    "expected_state_hash does not match latest completed shot_contracts_hash"
                )

        compile_started = utc_now()
        document = _compile(command)
        ir_payload = document.model_dump(mode="json")
        ir_hash = content_hash(document.model_dump_json())
        run = _checkpoint(
            active_store,
            run,
            CheckpointRecord(
                step=PipelineStepName.COMPILE,
                status=RunStatus.COMPLETED,
                started_at=compile_started,
                completed_at=utc_now(),
                output_hash=ir_hash,
            ),
        )

        ledger_started = utc_now()
        ledger = build_continuity_ledger(document)
        ledger_payload = ledger.model_dump(mode="json")
        ledger_hash = content_hash(ledger.model_dump_json(exclude={"diagnostics"}))
        run = _checkpoint(
            active_store,
            run,
            CheckpointRecord(
                step=PipelineStepName.LEDGER,
                status=RunStatus.COMPLETED,
                started_at=ledger_started,
                completed_at=utc_now(),
                output_hash=ledger_hash,
            ),
        )

        shots_started = utc_now()
        shots = compile_shot_contracts(document, ledger=ledger)
        shots_payload = shots.model_dump(mode="json")
        shots_hash = content_hash(shots.model_dump_json(exclude={"diagnostics"}))
        run = _checkpoint(
            active_store,
            run,
            CheckpointRecord(
                step=PipelineStepName.SHOTS,
                status=RunStatus.COMPLETED,
                started_at=shots_started,
                completed_at=utc_now(),
                output_hash=shots_hash,
            ),
        )

        artifacts = PipelineArtifacts(
            production_ir=ir_payload,
            continuity_ledger=ledger_payload,
            shot_contracts=shots_payload,
            production_ir_hash=ir_hash,
            ledger_hash=ledger_hash,
            shot_contracts_hash=shots_hash,
        )
        run = run.model_copy(
            update={
                "status": RunStatus.COMPLETED,
                "updated_at": utc_now(),
                "artifacts": artifacts,
                "error": None,
            }
        )
        return active_store.put(run)
    except Exception as exc:
        run = run.model_copy(
            update={
                "status": RunStatus.FAILED,
                "updated_at": utc_now(),
                "error": str(exc),
            }
        )
        active_store.put(run)
        raise PipelineError(str(exc)) from exc


def _compile(command: PipelineCommand) -> ScriptDocument:
    compiler = compile_fdx_text if command.format == "fdx" else compile_text
    return compiler(
        command.text,
        title=command.title,
        revision=command.revision,
        document_key=command.document_key,
    )


def _checkpoint(store: RunStore, run: WorkflowRun, checkpoint: CheckpointRecord) -> WorkflowRun:
    checkpoints = [*run.checkpoints, checkpoint]
    updated = run.model_copy(
        update={"checkpoints": checkpoints, "updated_at": utc_now(), "status": RunStatus.RUNNING}
    )
    return store.put(updated)


def _latest_completed_for_document(store: RunStore, command: PipelineCommand) -> WorkflowRun | None:
    if command.document_key is None:
        return None
    candidates = [
        run
        for run in store.list_runs()
        if run.status == RunStatus.COMPLETED
        and run.command.document_key == command.document_key
        and run.artifacts is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda run: run.updated_at)
