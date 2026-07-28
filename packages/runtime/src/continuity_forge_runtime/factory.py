"""Environment-selected production runtime wiring."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from continuity_forge_auth import (
    DEFAULT_AUTH_SERVICE,
    AuthService,
    bootstrap_dev_allowed,
    bootstrap_dev_tenant,
)
from continuity_forge_harness import DEFAULT_RUN_STORE, FileRunStore, RunStore
from continuity_forge_operator import DEFAULT_PROJECT_STORE, FileProjectStore, ProjectStore
from continuity_forge_providers import (
    ArtifactStore,
    ProviderGateway,
    get_gateway,
)


class ArtifactSink(Protocol):
    def put(self, candidate: Any) -> str: ...


@dataclass
class RuntimeContext:
    run_store: RunStore
    project_store: ProjectStore
    gateway: ProviderGateway
    auth: AuthService
    artifact_store: ArtifactSink | None
    backend: str


def build_runtime() -> RuntimeContext:
    """Construct stores/gateway from environment.

    Selection order for durable stores:
    1. CF_DATABASE_URL → Postgres*
    2. CF_STORE_ROOT → File*
    3. otherwise in-memory defaults
    """
    backend = "memory"
    run_store: RunStore = DEFAULT_RUN_STORE
    project_store: ProjectStore = DEFAULT_PROJECT_STORE

    database_url = os.environ.get("CF_DATABASE_URL") or os.environ.get("DATABASE_URL")
    store_root = os.environ.get("CF_STORE_ROOT")

    if database_url:
        from continuity_forge_persistence import PostgresProjectStore, PostgresRunStore

        run_store = PostgresRunStore(database_url)
        project_store = PostgresProjectStore(database_url, run_store=run_store)
        backend = "postgres"
    elif store_root:
        root = Path(store_root)
        run_store = FileRunStore(root / "runs")
        project_store = FileProjectStore(root / "projects", run_store=run_store)
        backend = "filesystem"

    artifact_store: ArtifactSink | None = None
    if os.environ.get("CF_S3_BUCKET") or os.environ.get("CF_S3_ENDPOINT"):
        from continuity_forge_persistence import S3ArtifactStore

        artifact_store = S3ArtifactStore()
        backend = f"{backend}+s3"
    elif store_root:
        artifact_store = ArtifactStore(Path(store_root) / "artifacts")
        if "filesystem" not in backend:
            backend = f"{backend}+fs-artifacts"

    auth = DEFAULT_AUTH_SERVICE
    if store_root:
        auth_path = Path(store_root) / "auth.json"
        auth.load(auth_path)
        # Persist any bootstrap into the same file (local/dev only; see bootstrap_dev_allowed).
        if bootstrap_dev_allowed() and not auth.list_tenants():
            bootstrap_dev_tenant(auth)
            auth.save(auth_path)
    elif bootstrap_dev_allowed() and not auth.list_tenants():
        bootstrap_dev_tenant(auth)

    gateway = get_gateway(os.environ.get("CF_PROVIDER"))
    return RuntimeContext(
        run_store=run_store,
        project_store=project_store,
        gateway=gateway,
        auth=auth,
        artifact_store=artifact_store,
        backend=backend,
    )


_RUNTIME: RuntimeContext | None = None


def get_runtime(*, refresh: bool = False) -> RuntimeContext:
    global _RUNTIME
    if _RUNTIME is None or refresh:
        _RUNTIME = build_runtime()
    return _RUNTIME


def reset_runtime() -> None:
    """Test helper to rebuild runtime from current env."""
    global _RUNTIME
    _RUNTIME = None
