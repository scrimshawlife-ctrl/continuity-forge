from pathlib import Path

from continuity_forge_harness import FileRunStore, PipelineCommand, execute_kernel_pipeline
from continuity_forge_operator import FileProjectStore, MutationEnvelope

SOURCE = "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n"


def test_file_run_store_roundtrip(tmp_path: Path) -> None:
    store = FileRunStore(tmp_path / "runs")
    run = execute_kernel_pipeline(
        PipelineCommand(
            actor_id="t",
            authorization_scope="kernel:pipeline",
            idempotency_key="persist-1",
            rationale="persist",
            text=SOURCE,
            document_key="d1",
        ),
        store=store,
    )
    reloaded = FileRunStore(tmp_path / "runs")
    found = reloaded.get(run.run_id)
    assert found is not None
    assert found.status.value == "completed"
    assert found.artifacts is not None


def test_file_project_store_roundtrip(tmp_path: Path) -> None:
    store = FileProjectStore(tmp_path / "projects")
    store.acquire_lease("p1", "op")
    project, _run = store.ingest_script(
        document_key="p1",
        title="P",
        text=SOURCE,
        revision="0.1.0",
        format="fountain",
        envelope=MutationEnvelope(
            actor_id="op",
            authorization_scope="kernel:pipeline",
            idempotency_key="ingest-persist",
            rationale="persist project",
        ),
    )
    reloaded = FileProjectStore(tmp_path / "projects")
    loaded = reloaded.get_project("p1")
    assert loaded is not None
    assert loaded.source_hash == project.source_hash
    assert loaded.production_ir is not None
