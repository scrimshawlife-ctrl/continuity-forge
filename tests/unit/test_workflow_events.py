"""Unit tests for workflow event ordering and idempotent replay (long-form 4.6)."""

from __future__ import annotations

import pytest
from continuity_forge_harness import (
    PipelineCommand,
    PipelineError,
    RunStatus,
    RunStore,
    WorkflowEventKind,
    build_event_page,
    events_from_workflow_run,
    execute_kernel_pipeline,
    filter_events_after,
    progress_from_run,
    redact_error,
    stream_fingerprint,
)

SOURCE = "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nHold.\n"


def _command(**overrides: object) -> PipelineCommand:
    payload: dict[str, object] = {
        "actor_id": "tester",
        "authorization_scope": "kernel:pipeline",
        "idempotency_key": "evt-1",
        "rationale": "event stream unit test",
        "text": SOURCE,
        "document_key": "events-doc",
        "title": "Events",
    }
    payload.update(overrides)
    return PipelineCommand.model_validate(payload)


def test_events_ordered_run_started_checkpoints_completed() -> None:
    store = RunStore()
    run = execute_kernel_pipeline(_command(), store=store)
    events = events_from_workflow_run(run)
    kinds = [e.kind for e in events]
    assert kinds[0] == WorkflowEventKind.RUN_STARTED
    assert kinds[-1] == WorkflowEventKind.RUN_COMPLETED
    assert kinds.count(WorkflowEventKind.CHECKPOINT) == 3
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    assert events[1].step == "compile_screenplay"
    assert events[2].step == "build_continuity_ledger"
    assert events[3].step == "compile_shot_contracts"
    # Non-canon refs only
    assert "text" not in events[0].payload_ref
    assert events[0].payload_ref.get("command_hash")
    assert run.artifacts is not None
    assert events[-1].payload_ref.get("shot_contracts_hash") == run.artifacts.shot_contracts_hash


def test_event_stream_idempotent_replay() -> None:
    store = RunStore()
    first = execute_kernel_pipeline(_command(idempotency_key="same-evt"), store=store)
    second = execute_kernel_pipeline(_command(idempotency_key="same-evt"), store=store)
    assert first.run_id == second.run_id
    e1 = events_from_workflow_run(first)
    e2 = events_from_workflow_run(second)
    assert [e.event_id for e in e1] == [e.event_id for e in e2]
    assert stream_fingerprint(e1) == stream_fingerprint(e2)
    # Idempotent completed return does not re-execute or change checkpoints
    assert first.checkpoints == second.checkpoints


def test_filter_events_after_sequence_and_last_event_id() -> None:
    store = RunStore()
    run = execute_kernel_pipeline(_command(idempotency_key="cursor"), store=store)
    events = events_from_workflow_run(run)
    after_two = filter_events_after(events, after_sequence=2)
    assert after_two[0].sequence == 3
    mid = events[2]
    after_id = filter_events_after(events, last_event_id=mid.event_id)
    assert after_id[0].sequence == mid.sequence + 1
    page = build_event_page(run, after_sequence=0)
    assert page.transport == "poll"
    assert page.workflow_complete_is_not_production_ready is True
    assert page.claim == "workflow_events_observability_not_canon"
    resume = build_event_page(run, last_event_id=page.events[0].event_id)
    assert resume.events[0].sequence == 2
    assert resume.next_after_sequence == page.next_after_sequence


def test_progress_percent_and_labels() -> None:
    store = RunStore()
    run = execute_kernel_pipeline(_command(idempotency_key="prog"), store=store)
    progress = progress_from_run(run)
    assert progress.percent == 100
    assert progress.completed_steps == 3
    assert progress.total_steps == 3
    assert progress.workflow_complete_is_not_production_ready is True
    assert "production ready" in progress.note.lower()
    assert progress.last_successful_checkpoint == "compile_shot_contracts"


def test_failed_run_exposes_last_checkpoint_and_redacted_error() -> None:
    store = RunStore()
    # Force fail via expected_state_hash mismatch after a successful first run
    first = execute_kernel_pipeline(_command(idempotency_key="fail-a"), store=store)
    assert first.status == RunStatus.COMPLETED
    with pytest.raises(PipelineError):
        execute_kernel_pipeline(
            _command(
                idempotency_key="fail-b",
                expected_state_hash="0" * 64,
                text=SOURCE + "\nLater.\n",
                revision="0.2.0",
            ),
            store=store,
        )
    failed = next(r for r in store.list_runs() if r.status == RunStatus.FAILED)
    events = events_from_workflow_run(failed)
    assert events[-1].kind == WorkflowEventKind.RUN_FAILED
    assert events[-1].payload_ref.get("error_code") == "pipeline_failed"
    progress = progress_from_run(failed)
    assert progress.error_code == "pipeline_failed"
    assert progress.error_message
    # Failed early: no successful checkpoints
    assert progress.percent < 100

    # Redaction strips secret-like substrings
    dirty = "failed api_key=sk-live-secret-xyz bearer TOKEN"
    clean = redact_error(dirty)
    assert clean is not None
    assert "sk-live" not in clean
    assert "[redacted]" in clean


def test_event_page_does_not_include_script_source() -> None:
    store = RunStore()
    run = execute_kernel_pipeline(_command(idempotency_key="nosrc"), store=store)
    page = build_event_page(run)
    blob = page.model_dump_json()
    assert "red keycard" not in blob
    assert SOURCE not in blob
