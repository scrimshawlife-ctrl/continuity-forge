import pytest
from continuity_forge_compiler import compile_text
from continuity_forge_harness import (
    InProcessWorker,
    PipelineCommand,
    try_build_temporal_worker_note,
)
from continuity_forge_providers import get_gateway, get_worker, list_providers
from continuity_forge_shots import compile_shot_contracts

SOURCE = "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n"


def test_in_process_worker_runs_pipeline() -> None:
    worker = InProcessWorker()
    command = PipelineCommand(
        actor_id="w",
        authorization_scope="kernel:pipeline",
        idempotency_key="worker-1",
        rationale="worker test",
        text=SOURCE,
        document_key="worker-doc",
    )
    result = worker.run_workflow(command)
    assert result["status"] == "completed"
    assert "run_kernel_pipeline" in worker.list_activities()
    step = worker.execute(
        "compile_screenplay",
        command.model_dump(mode="json"),
    )
    assert step["step"] == "compile_screenplay"
    note = try_build_temporal_worker_note()
    assert "temporalio_installed" in note


def test_provider_registry_defaults_to_mock() -> None:
    assert "mock" in list_providers()
    worker = get_worker("mock")
    document = compile_text(SOURCE, document_key="reg")
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    candidate = get_gateway("mock").generate_for_shot(contract, seed="1")
    assert candidate.provider == "mock"
    assert worker.provider == "mock"  # type: ignore[attr-defined]


def test_unconfigured_real_provider_fails_closed() -> None:
    document = compile_text(SOURCE, document_key="reg2")
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY|not installed"):
        get_gateway("openai").generate_for_shot(contract, seed="1")
