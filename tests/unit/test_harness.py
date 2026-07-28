import pytest
from continuity_forge_harness import (
    ACTIVITY_NAMES,
    PipelineCommand,
    PipelineError,
    RunStatus,
    RunStore,
    execute_kernel_pipeline,
    temporal_registration_manifest,
    workflow_id_for,
)

SOURCE = "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nHold.\n"


def _command(**overrides: object) -> PipelineCommand:
    payload: dict[str, object] = {
        "actor_id": "tester",
        "authorization_scope": "kernel:pipeline",
        "idempotency_key": "run-1",
        "rationale": "unit test pipeline",
        "text": SOURCE,
        "document_key": "harness-doc",
        "title": "Harness",
    }
    payload.update(overrides)
    return PipelineCommand.model_validate(payload)


def test_pipeline_runs_compile_ledger_and_shots() -> None:
    store = RunStore()
    run = execute_kernel_pipeline(_command(), store=store)
    assert run.status == RunStatus.COMPLETED
    assert run.artifacts is not None
    assert run.artifacts.production_ir["scenes"]
    assert run.artifacts.continuity_ledger["entities"]
    assert run.artifacts.shot_contracts["contracts"]
    assert [cp.step.value for cp in run.checkpoints] == [
        "compile_screenplay",
        "build_continuity_ledger",
        "compile_shot_contracts",
    ]
    assert all(cp.status == RunStatus.COMPLETED for cp in run.checkpoints)


def test_idempotent_replay_returns_same_completed_run() -> None:
    store = RunStore()
    first = execute_kernel_pipeline(_command(idempotency_key="same"), store=store)
    second = execute_kernel_pipeline(_command(idempotency_key="same"), store=store)
    assert first.run_id == second.run_id
    assert first.artifacts == second.artifacts
    assert second.attempt == 1


def test_idempotency_conflict_on_payload_change() -> None:
    store = RunStore()
    execute_kernel_pipeline(_command(idempotency_key="conflict"), store=store)
    with pytest.raises(PipelineError, match="different command payload"):
        execute_kernel_pipeline(
            _command(idempotency_key="conflict", text=SOURCE + "\nExtra.\n"),
            store=store,
        )


def test_expected_state_hash_guards_document_revision() -> None:
    store = RunStore()
    first = execute_kernel_pipeline(_command(idempotency_key="a"), store=store)
    assert first.artifacts is not None
    ok = execute_kernel_pipeline(
        _command(
            idempotency_key="b",
            expected_state_hash=first.artifacts.shot_contracts_hash,
            text=SOURCE + "\nA beat later.\n",
            revision="0.2.0",
        ),
        store=store,
    )
    assert ok.status == RunStatus.COMPLETED
    with pytest.raises(PipelineError, match="expected_state_hash"):
        execute_kernel_pipeline(
            _command(
                idempotency_key="c",
                expected_state_hash="0" * 64,
                text=SOURCE + "\nAnother.\n",
                revision="0.3.0",
            ),
            store=store,
        )


def test_temporal_adapter_contracts_are_stable() -> None:
    manifest = temporal_registration_manifest()
    assert manifest["workflow_type"] == "KernelPipelineWorkflow"
    assert manifest["task_queue"] == "continuity-forge-kernel"
    assert set(manifest["activities"]) == set(ACTIVITY_NAMES)
    command = _command()
    assert workflow_id_for(command) == f"kernel-pipeline:{command.idempotency_key}"
