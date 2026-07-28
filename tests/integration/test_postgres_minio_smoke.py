"""Phase 2 integration smoke: Postgres + MinIO/S3.

Skip-friendly locally: when optional deps or services are missing, tests
``pytest.skip`` instead of failing. CI job ``ci-integration.yml`` provides
``postgres:16`` + MinIO and sets ``CF_DATABASE_URL`` / ``CF_S3_*``.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

# Marker is registered in pyproject.toml; also applied via pytestmark for clarity.
pytestmark = pytest.mark.integration

SOURCE = "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n"


def _database_url() -> str | None:
    return os.environ.get("CF_DATABASE_URL") or os.environ.get("DATABASE_URL")


def _require_postgres() -> str:
    """Return DSN or skip when psycopg/env/service is unavailable."""
    pytest.importorskip("psycopg")
    url = _database_url()
    if not url:
        pytest.skip("CF_DATABASE_URL / DATABASE_URL not set (Postgres integration skipped)")
    import psycopg

    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 — any connect failure → skip locally
        pytest.skip(f"Postgres unreachable at CF_DATABASE_URL: {exc}")
    return url


def _require_s3_env() -> dict[str, str]:
    """Return S3/MinIO settings or skip when boto3/env/service is unavailable."""
    pytest.importorskip("boto3")
    endpoint = os.environ.get("CF_S3_ENDPOINT") or os.environ.get("AWS_ENDPOINT_URL")
    if not endpoint:
        pytest.skip("CF_S3_ENDPOINT / AWS_ENDPOINT_URL not set (S3/MinIO integration skipped)")

    access = (
        os.environ.get("CF_S3_ACCESS_KEY") or os.environ.get("AWS_ACCESS_KEY_ID") or "minioadmin"
    )
    secret = (
        os.environ.get("CF_S3_SECRET_KEY")
        or os.environ.get("AWS_SECRET_ACCESS_KEY")
        or "minioadmin"
    )
    region = os.environ.get("CF_S3_REGION") or os.environ.get("AWS_REGION") or "us-east-1"
    bucket = os.environ.get("CF_S3_BUCKET") or "continuity-forge"

    import boto3
    from botocore.client import Config
    from botocore.exceptions import BotoCoreError, ClientError

    client: Any = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name=region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        client.list_buckets()
    except (BotoCoreError, ClientError, OSError) as exc:
        pytest.skip(f"MinIO/S3 unreachable at {endpoint}: {exc}")

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        try:
            client.create_bucket(Bucket=bucket)
        except ClientError as exc:
            pytest.skip(f"Could not create/access bucket {bucket!r}: {exc}")

    return {
        "endpoint": endpoint,
        "access": access,
        "secret": secret,
        "region": region,
        "bucket": bucket,
    }


def test_postgres_run_store_roundtrip() -> None:
    """Minimal Postgres durability: put WorkflowRun, rehydrate, read back."""
    dsn = _require_postgres()

    from continuity_forge_harness import PipelineCommand, RunStatus, execute_kernel_pipeline
    from continuity_forge_persistence import PostgresRunStore

    writer = PostgresRunStore(dsn)
    run = execute_kernel_pipeline(
        PipelineCommand(
            actor_id="ci-integration",
            authorization_scope="kernel:pipeline",
            idempotency_key="integration-postgres-smoke-1",
            rationale="postgres integration smoke",
            text=SOURCE,
            document_key="integration-smoke",
        ),
        store=writer,
    )
    assert run.status == RunStatus.COMPLETED

    reader = PostgresRunStore(dsn)
    found = reader.get(run.run_id)
    assert found is not None
    assert found.run_id == run.run_id
    assert found.status == RunStatus.COMPLETED
    assert found.idempotency_key == "integration-postgres-smoke-1"
    assert found.command.document_key == "integration-smoke"
    assert found.artifacts is not None


def test_minio_s3_artifact_store_roundtrip() -> None:
    """Minimal MinIO durability: put PROPOSED artifact candidate, get by content hash."""
    cfg = _require_s3_env()

    from continuity_forge_compiler import compile_text
    from continuity_forge_persistence import S3ArtifactStore
    from continuity_forge_providers import get_gateway
    from continuity_forge_shots import compile_shot_contracts

    # Ensure env matches what Boto3ObjectClient / S3ArtifactStore read.
    os.environ.setdefault("CF_S3_ENDPOINT", cfg["endpoint"])
    os.environ.setdefault("CF_S3_BUCKET", cfg["bucket"])
    os.environ.setdefault("CF_S3_ACCESS_KEY", cfg["access"])
    os.environ.setdefault("CF_S3_SECRET_KEY", cfg["secret"])
    os.environ.setdefault("CF_S3_REGION", cfg["region"])
    os.environ.setdefault("AWS_ACCESS_KEY_ID", cfg["access"])
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", cfg["secret"])

    document = compile_text(SOURCE, document_key="integration-s3-smoke")
    contracts = compile_shot_contracts(document).contracts
    assert contracts, "expected at least one shot contract from smoke fountain"
    candidate = get_gateway("mock").generate_for_shot(
        contracts[0].model_dump(mode="json"),
        seed="integration-s3",
    )

    store = S3ArtifactStore(bucket=cfg["bucket"])
    digest = store.put(candidate)
    loaded = store.get(digest)
    assert loaded is not None
    assert loaded["content_hash"] == candidate.content_hash
    assert digest in store.list_hashes()
