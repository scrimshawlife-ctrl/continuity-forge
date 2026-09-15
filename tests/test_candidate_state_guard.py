"""Candidate writes bind to project state without promoting canon."""

import pytest
from continuity_forge_auth import AuthService
from continuity_forge_harness import RunStore
from continuity_forge_mcp import server
from continuity_forge_operator import MutationEnvelope, OperatorError, ProjectStore
from continuity_forge_providers import ArtifactStore, ProviderGateway
from continuity_forge_runtime.factory import RuntimeContext


@pytest.fixture
def candidate_runtime(monkeypatch, tmp_path):
    runs = RunStore()
    store = ProjectStore(run_store=runs)
    runtime = RuntimeContext(
        runs, store, ProviderGateway(), AuthService(), ArtifactStore(tmp_path / "artifacts"), "test"
    )
    monkeypatch.setattr(server, "_rt", lambda: runtime)
    project, _ = store.ingest_script(
        document_key="film",
        title="Film",
        text="INT. ROOM - DAY\n\nMara returns a key.\n",
        revision="1",
        format="fountain",
        require_lease=False,
        envelope=MutationEnvelope.from_parts(
            actor_id="test",
            authorization_scope="kernel:pipeline",
            idempotency_key="initial",
            rationale="test fixture",
        ),
    )
    return runtime, project, tmp_path / "artifacts"


@pytest.mark.parametrize("tool", [server.queue_generation, server.run_shot_repair_loop])
def test_stale_candidate_hash_rejected_before_provider_or_persistence(
    candidate_runtime, tool, monkeypatch
):
    runtime, project, artifacts = candidate_runtime

    def forbidden(*args, **kwargs):
        pytest.fail("provider called with stale project state")

    monkeypatch.setattr(runtime.gateway, "generate_for_shot", forbidden)
    with pytest.raises(OperatorError, match="expected_state_hash conflict"):
        tool(
            "film", project.shot_contracts["contracts"][0]["shot_id"], expected_state_hash="0" * 64
        )
    assert not list(artifacts.rglob("*.json"))


@pytest.mark.parametrize("tool", [server.queue_generation, server.run_shot_repair_loop])
def test_revision_between_snapshot_and_guard_is_rejected(candidate_runtime, tool, monkeypatch):
    runtime, project, artifacts = candidate_runtime
    get_project = runtime.project_store.get_project
    generate = runtime.gateway.generate_for_shot
    reads = 0

    def racing_read(key):
        nonlocal reads
        snapshot = get_project(key)
        reads += 1
        if reads == 1:
            reingest(runtime, project)
        return snapshot

    def forbidden(*args, **kwargs):
        pytest.fail("generation preceded current-state validation")

    monkeypatch.setattr(runtime.project_store, "get_project", racing_read)
    monkeypatch.setattr(runtime.gateway, "generate_for_shot", forbidden)
    with pytest.raises(OperatorError, match="expected_state_hash conflict"):
        tool("film", project.shot_contracts["contracts"][0]["shot_id"])
    assert not list(artifacts.rglob("*.json"))
    monkeypatch.setattr(runtime.gateway, "generate_for_shot", generate)


@pytest.mark.parametrize("tool", [server.queue_generation, server.run_shot_repair_loop])
@pytest.mark.parametrize("explicit", [False, True])
def test_candidate_guard_holds_through_persistence(candidate_runtime, tool, monkeypatch, explicit):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    runtime, project, artifacts = candidate_runtime
    attempted = Event()
    completed = Event()
    put = runtime.artifact_store.put
    future = None

    def revise():
        attempted.set()
        result = reingest(runtime, project)
        completed.set()
        return result

    with ThreadPoolExecutor(max_workers=1) as pool:

        def checked_put(candidate):
            nonlocal future
            future = pool.submit(revise)
            assert attempted.wait(5)
            assert not completed.wait(0.1), "revision committed before candidate persistence"
            assert runtime.project_store.get_project("film").state_hash == project.state_hash
            return put(candidate)

        monkeypatch.setattr(runtime.artifact_store, "put", checked_put)
        kwargs = {"expected_state_hash": project.state_hash} if explicit else {}
        result = tool("film", project.shot_contracts["contracts"][0]["shot_id"], **kwargs)
        assert future is not None
        revised, _ = future.result(timeout=5)
    assert revised.state_hash != project.state_hash
    assert result.get("authority", result.get("status")) in {"PROPOSED", "accepted_proposed"}
    candidate = result.get("accepted_candidate", result)
    assert ArtifactStore(artifacts).get(candidate["content_hash"]) == candidate


def reingest(runtime, project):
    return runtime.project_store.ingest_script(
        document_key="film",
        title="Film",
        text="INT. ROOM - DAY\n\nMara drops a key.\n",
        revision="2",
        format="fountain",
        require_lease=False,
        envelope=MutationEnvelope.from_parts(
            actor_id="test",
            authorization_scope="kernel:pipeline",
            idempotency_key="revision",
            rationale="concurrent revision",
            expected_state_hash=project.state_hash,
        ),
    )


@pytest.mark.parametrize("tool", [server.queue_generation, server.run_shot_repair_loop])
def test_reentrant_revision_during_generation_cannot_persist_stale_candidate(
    candidate_runtime, tool, monkeypatch
):
    runtime, project, artifacts = candidate_runtime
    generate = runtime.gateway.generate_for_shot
    revised = False

    def revise_then_generate(*args, **kwargs):
        nonlocal revised
        if not revised:
            revised = True
            reingest(runtime, project)
        return generate(*args, **kwargs)

    monkeypatch.setattr(runtime.gateway, "generate_for_shot", revise_then_generate)
    with pytest.raises(OperatorError, match="expected_state_hash conflict"):
        tool("film", project.shot_contracts["contracts"][0]["shot_id"])
    assert not list(artifacts.rglob("*.json"))
