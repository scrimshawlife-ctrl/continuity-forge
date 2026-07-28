import json

from continuity_forge_harness import build_worker_spec, worker_cli


def test_build_worker_spec_defaults() -> None:
    spec = build_worker_spec()
    assert spec.workflow_type == "KernelPipelineWorkflow"
    assert spec.task_queue == "continuity-forge-kernel"
    assert "run_kernel_pipeline" in spec.activities
    assert spec.namespace == "default"


def test_worker_cli_check_prints_spec(capsys: object) -> None:
    code = worker_cli(["--check", "--host", "example:7233", "--namespace", "cf"])
    assert code == 0
    # pytest injects capsys; read via attribute protocol
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)
    assert payload["workflow_type"] == "KernelPipelineWorkflow"
    assert payload["target_host"] == "example:7233"
    assert payload["namespace"] == "cf"


def test_worker_cli_run_without_temporalio_fails_closed() -> None:
    try:
        import temporalio  # noqa: F401
    except ImportError:
        code = worker_cli([])
        assert code == 2
    else:
        # Avoid connecting to a real cluster in unit tests.
        assert True
