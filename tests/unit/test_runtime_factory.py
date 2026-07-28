import os
from pathlib import Path

from continuity_forge_harness import FileRunStore
from continuity_forge_operator import FileProjectStore
from continuity_forge_providers import ArtifactStore
from continuity_forge_runtime import build_runtime, reset_runtime


def test_runtime_defaults_to_memory() -> None:
    os.environ.pop("CF_DATABASE_URL", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("CF_STORE_ROOT", None)
    os.environ.pop("CF_S3_BUCKET", None)
    os.environ.pop("CF_S3_ENDPOINT", None)
    reset_runtime()
    rt = build_runtime()
    assert rt.backend == "memory"
    assert rt.artifact_store is None


def test_runtime_selects_filesystem(tmp_path: Path) -> None:
    os.environ.pop("CF_DATABASE_URL", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("CF_S3_BUCKET", None)
    os.environ.pop("CF_S3_ENDPOINT", None)
    os.environ["CF_STORE_ROOT"] = str(tmp_path)
    try:
        reset_runtime()
        rt = build_runtime()
        assert "filesystem" in rt.backend
        assert isinstance(rt.run_store, FileRunStore)
        assert isinstance(rt.project_store, FileProjectStore)
        assert isinstance(rt.artifact_store, ArtifactStore)
    finally:
        os.environ.pop("CF_STORE_ROOT", None)
        reset_runtime()
