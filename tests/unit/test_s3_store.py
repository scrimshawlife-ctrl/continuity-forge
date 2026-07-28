from continuity_forge_compiler import compile_text
from continuity_forge_persistence import S3ArtifactStore
from continuity_forge_providers import get_gateway
from continuity_forge_shots import compile_shot_contracts


class _MemoryObjectClient:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, *, bucket: str, key: str, body: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = body

    def get_object(self, *, bucket: str, key: str) -> bytes | None:
        return self.objects.get((bucket, key))

    def list_keys(self, *, bucket: str, prefix: str) -> list[str]:
        return [k for (b, k) in self.objects if b == bucket and k.startswith(prefix)]


def test_s3_artifact_store_with_memory_client() -> None:
    document = compile_text(
        "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n",
        document_key="s3-doc",
    )
    contract = compile_shot_contracts(document).contracts[0].model_dump(mode="json")
    candidate = get_gateway("mock").generate_for_shot(contract, seed="s3")
    client = _MemoryObjectClient()
    store = S3ArtifactStore(bucket="cf", client=client)
    digest = store.put(candidate)
    loaded = store.get(digest)
    assert loaded is not None
    assert loaded["content_hash"] == candidate.content_hash
    assert digest in store.list_hashes()
