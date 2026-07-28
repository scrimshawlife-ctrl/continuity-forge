import pytest
from continuity_forge_operator import (
    MutationEnvelope,
    OperatorError,
    ProjectStore,
)

SOURCE_V1 = "INT. A - DAY\n\nAction.\n"
SOURCE_V2 = "INT. A - DAY\n\nAction revised.\n"


def _envelope(
    actor: str = "a",
    key: str = "k1",
    expected: str | None = None,
) -> MutationEnvelope:
    return MutationEnvelope.from_parts(
        actor_id=actor,
        authorization_scope="kernel:pipeline",
        idempotency_key=key,
        rationale="test",
        expected_state_hash=expected,
    )


def test_ingest_requires_lease_and_stores_artifacts() -> None:
    store = ProjectStore()
    with pytest.raises(OperatorError, match="write lease"):
        store.ingest_script(
            document_key="p1",
            title="P",
            text=SOURCE_V1,
            revision="0.1.0",
            format="fountain",
            envelope=_envelope(),
        )
    store.acquire_lease("p1", "a")
    project, run = store.ingest_script(
        document_key="p1",
        title="P",
        text=SOURCE_V1,
        revision="0.1.0",
        format="fountain",
        envelope=_envelope(),
    )
    assert project.production_ir is not None
    assert project.state_hash is not None
    assert run.status.value == "completed"
    status = store.resource("cf://projects/p1/status")
    assert status is not None
    assert status["scene_count"] == 1
    ir = store.resource("cf://projects/p1/production-ir")
    assert ir is not None
    assert ir["scenes"]


def test_write_lease_blocks_other_actor() -> None:
    """Two holders cannot both hold an exclusive write lease."""
    store = ProjectStore()
    store.acquire_lease("p2", "alice")
    with pytest.raises(OperatorError, match="write lease held"):
        store.acquire_lease("p2", "bob")
    store.release_lease("p2", "alice")
    lease = store.acquire_lease("p2", "bob")
    assert lease.holder == "bob"
    assert store.get_lease("p2") is not None
    assert store.get_lease("p2").holder == "bob"  # type: ignore[union-attr]
    store.release_lease("p2", "bob")
    assert store.get_lease("p2") is None


def test_write_lease_exclusivity_two_holders_cannot_mutate() -> None:
    """Lease exclusivity: non-holder is blocked from acquire and from mutate."""
    store = ProjectStore()
    store.acquire_lease("p-exclusive", "holder-a")

    # Second holder cannot acquire while first holds.
    with pytest.raises(OperatorError, match="write lease held by holder-a"):
        store.acquire_lease("p-exclusive", "holder-b")

    # Non-holder cannot mutate even if they ignore acquire failure.
    with pytest.raises(OperatorError, match="does not hold the write lease"):
        store.ingest_script(
            document_key="p-exclusive",
            title="X",
            text=SOURCE_V1,
            revision="0.1.0",
            format="fountain",
            envelope=_envelope(actor="holder-b", key="k-b"),
        )

    # Holder can mutate.
    project, _ = store.ingest_script(
        document_key="p-exclusive",
        title="X",
        text=SOURCE_V1,
        revision="0.1.0",
        format="fountain",
        envelope=_envelope(actor="holder-a", key="k-a"),
    )
    assert project.state_hash is not None

    # Non-holder still cannot release the lease.
    with pytest.raises(OperatorError, match="only the lease holder"):
        store.release_lease("p-exclusive", "holder-b")

    store.release_lease("p-exclusive", "holder-a")
    # After release, the other actor may acquire exclusivity.
    lease = store.acquire_lease("p-exclusive", "holder-b")
    assert lease.holder == "holder-b"


def test_same_holder_may_refresh_lease() -> None:
    store = ProjectStore()
    first = store.acquire_lease("p-refresh", "alice", ttl_seconds=60)
    second = store.acquire_lease("p-refresh", "alice", ttl_seconds=120)
    assert second.holder == "alice"
    assert second.expires_at >= first.expires_at


def test_expected_state_hash_required_on_reingest() -> None:
    store = ProjectStore()
    store.acquire_lease("p-state", "a")
    project, _ = store.ingest_script(
        document_key="p-state",
        title="P",
        text=SOURCE_V1,
        revision="0.1.0",
        format="fountain",
        envelope=_envelope(key="ingest-1"),
    )
    assert project.state_hash is not None

    with pytest.raises(OperatorError, match="expected_state_hash required"):
        store.ingest_script(
            document_key="p-state",
            title="P",
            text=SOURCE_V2,
            revision="0.2.0",
            format="fountain",
            envelope=_envelope(key="ingest-2"),
        )


def test_expected_state_hash_conflict_on_stale_hash() -> None:
    store = ProjectStore()
    store.acquire_lease("p-conflict", "a")
    project, _ = store.ingest_script(
        document_key="p-conflict",
        title="P",
        text=SOURCE_V1,
        revision="0.1.0",
        format="fountain",
        envelope=_envelope(key="c1"),
    )
    stale = "0" * 64
    with pytest.raises(OperatorError, match="expected_state_hash conflict"):
        store.ingest_script(
            document_key="p-conflict",
            title="P",
            text=SOURCE_V2,
            revision="0.2.0",
            format="fountain",
            envelope=_envelope(key="c2", expected=stale),
        )

    # Matching hash allows re-ingest.
    updated, _ = store.ingest_script(
        document_key="p-conflict",
        title="P",
        text=SOURCE_V2,
        revision="0.2.0",
        format="fountain",
        envelope=_envelope(key="c3", expected=project.state_hash),
    )
    assert updated.state_hash is not None
    assert updated.state_hash != project.state_hash
    assert updated.source_text == SOURCE_V2


def test_mutation_envelope_from_parts_is_universal_contract() -> None:
    env = MutationEnvelope.from_parts(
        actor_id="op",
        authorization_scope="kernel:pipeline",
        idempotency_key="id-1",
        rationale="contract",
    )
    assert env.command_schema_version == "m4.operator.v1"
    assert env.expected_state_hash is None
