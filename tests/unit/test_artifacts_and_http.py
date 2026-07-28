from pathlib import Path
from typing import Any

import pytest
from continuity_forge_compiler import compile_text
from continuity_forge_providers import (
    ArtifactStore,
    HttpMediaWorker,
    WorkerTask,
    get_gateway,
)
from continuity_forge_shots import compile_shot_contracts

SOURCE = "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n"


def _contract() -> dict[str, Any]:
    document = compile_text(SOURCE, document_key="http-doc")
    return compile_shot_contracts(document).contracts[0].model_dump(mode="json")


def test_artifact_store_roundtrip(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")
    candidate = get_gateway("mock").generate_for_shot(_contract(), seed="a")
    digest = store.put(candidate)
    loaded = store.get(digest)
    assert loaded is not None
    assert loaded["content_hash"] == candidate.content_hash
    assert digest in store.list_hashes()


def test_http_worker_dry_run_without_url() -> None:
    worker = HttpMediaWorker(base_url="", dry_run=True)
    candidate = worker.generate(shot_contract=_contract(), task=WorkerTask.IMAGE, seed="1")
    assert candidate.authority.value == "PROPOSED"
    assert candidate.content_hash


class _FakeTransport:
    def __init__(self, body: dict[str, Any]) -> None:
        self.body = body
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((url, payload))
        return self.body


def test_http_worker_posts_and_wraps_remote_payload() -> None:
    transport = _FakeTransport({"provider": "custom", "model": "x", "ok": True})
    worker = HttpMediaWorker(
        base_url="http://provider.local",
        transport=transport,
        dry_run=False,
    )
    candidate = worker.generate(shot_contract=_contract(), task=WorkerTask.IMAGE, seed="9")
    assert transport.calls
    assert transport.calls[0][0].endswith("/v1/generate")
    assert candidate.provider == "custom"
    assert candidate.payload.get("remote", {}).get("ok") is True


def test_openai_without_key_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY|not installed"):
        get_gateway("openai").generate_for_shot(_contract(), seed="1")
