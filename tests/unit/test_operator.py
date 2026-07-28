import pytest
from continuity_forge_operator import (
    MutationEnvelope,
    OperatorError,
    ProjectStore,
)


def test_ingest_requires_lease_and_stores_artifacts() -> None:
    store = ProjectStore()
    with pytest.raises(OperatorError, match="write lease"):
        store.ingest_script(
            document_key="p1",
            title="P",
            text="INT. A - DAY\n\nAction.\n",
            revision="0.1.0",
            format="fountain",
            envelope=MutationEnvelope(
                actor_id="a",
                authorization_scope="kernel:pipeline",
                idempotency_key="k1",
                rationale="test",
            ),
        )
    store.acquire_lease("p1", "a")
    project, run = store.ingest_script(
        document_key="p1",
        title="P",
        text="INT. A - DAY\n\nAction.\n",
        revision="0.1.0",
        format="fountain",
        envelope=MutationEnvelope(
            actor_id="a",
            authorization_scope="kernel:pipeline",
            idempotency_key="k1",
            rationale="test",
        ),
    )
    assert project.production_ir is not None
    assert run.status.value == "completed"
    status = store.resource("cf://projects/p1/status")
    assert status is not None
    assert status["scene_count"] == 1
    ir = store.resource("cf://projects/p1/production-ir")
    assert ir is not None
    assert ir["scenes"]


def test_write_lease_blocks_other_actor() -> None:
    store = ProjectStore()
    store.acquire_lease("p2", "alice")
    with pytest.raises(OperatorError, match="write lease held"):
        store.acquire_lease("p2", "bob")
    store.release_lease("p2", "alice")
    lease = store.acquire_lease("p2", "bob")
    assert lease.holder == "bob"
