"""PostgreSQL-backed run and project stores (optional psycopg)."""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from continuity_forge_harness import RunStore, WorkflowRun
from continuity_forge_operator import (
    ApprovalRecord,
    ApprovalStatus,
    MutationEnvelope,
    ProjectRecord,
    ProjectStore,
    WriteLease,
)

# WorkflowRun is re-exported for type checkers via ingest return


def _connect(dsn: str | None = None) -> Any:
    try:
        import psycopg  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "psycopg not installed. pip install 'continuity-forge[postgres]'"
        ) from exc
    url = dsn or os.environ.get("CF_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("CF_DATABASE_URL / DATABASE_URL is required for Postgres stores")
    return psycopg.connect(url)


class PostgresRunStore(RunStore):
    """RunStore using a Postgres table for durability."""

    def __init__(self, dsn: str | None = None) -> None:
        super().__init__()
        self.dsn = dsn
        self._ensure_schema()
        self._hydrate()

    def _ensure_schema(self) -> None:
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            conn.commit()

    def _hydrate(self) -> None:
        with _connect(self.dsn) as conn:
            rows = conn.execute("SELECT payload FROM cf_workflow_runs").fetchall()
        for (payload,) in rows:
            run = WorkflowRun.model_validate(payload)
            self._by_id[run.run_id] = run
            self._by_idempotency[run.idempotency_key] = run.run_id

    def put(self, run: WorkflowRun) -> WorkflowRun:
        stored = super().put(run)
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO cf_workflow_runs (run_id, idempotency_key, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (run_id) DO UPDATE
                SET payload = EXCLUDED.payload,
                    idempotency_key = EXCLUDED.idempotency_key,
                    updated_at = NOW()
                """,
                (
                    str(stored.run_id),
                    stored.idempotency_key,
                    json.dumps(stored.model_dump(mode="json")),
                ),
            )
            conn.commit()
        return stored


class PostgresProjectStore(ProjectStore):
    """ProjectStore with Postgres persistence for projects/leases/approvals."""

    def __init__(self, dsn: str | None = None, run_store: RunStore | None = None) -> None:
        runs = run_store or PostgresRunStore(dsn)
        super().__init__(run_store=runs)
        self.dsn = dsn
        self._ensure_schema()
        self._hydrate()

    def _ensure_schema(self) -> None:
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_projects (
                    document_key TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_leases (
                    document_key TEXT PRIMARY KEY,
                    payload JSONB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cf_approvals (
                    approval_id TEXT PRIMARY KEY,
                    document_key TEXT NOT NULL,
                    payload JSONB NOT NULL
                )
                """
            )
            conn.commit()

    def _hydrate(self) -> None:
        with _connect(self.dsn) as conn:
            for (payload,) in conn.execute("SELECT payload FROM cf_projects").fetchall():
                project = ProjectRecord.model_validate(payload)
                self._projects[project.document_key] = project
            for (payload,) in conn.execute("SELECT payload FROM cf_leases").fetchall():
                lease = WriteLease.model_validate(payload)
                self._leases[lease.document_key] = lease
            for (payload,) in conn.execute("SELECT payload FROM cf_approvals").fetchall():
                approval = ApprovalRecord.model_validate(payload)
                self._approvals[approval.approval_id] = approval

    def _persist_project(self, project: ProjectRecord, tenant_id: str = "default") -> None:
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO cf_projects (document_key, tenant_id, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (document_key) DO UPDATE
                SET payload = EXCLUDED.payload,
                    tenant_id = EXCLUDED.tenant_id,
                    updated_at = NOW()
                """,
                (
                    project.document_key,
                    tenant_id,
                    json.dumps(project.model_dump(mode="json")),
                ),
            )
            conn.commit()

    def acquire_lease(
        self,
        document_key: str,
        holder: str,
        *,
        scope: str = "project",
        ttl_seconds: int = 300,
    ) -> WriteLease:
        lease = super().acquire_lease(document_key, holder, scope=scope, ttl_seconds=ttl_seconds)
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO cf_leases (document_key, payload)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (document_key) DO UPDATE SET payload = EXCLUDED.payload
                """,
                (document_key, json.dumps(lease.model_dump(mode="json"))),
            )
            conn.commit()
        return lease

    def release_lease(self, document_key: str, holder: str) -> None:
        super().release_lease(document_key, holder)
        with _connect(self.dsn) as conn:
            conn.execute("DELETE FROM cf_leases WHERE document_key = %s", (document_key,))
            conn.commit()

    def ingest_script(
        self,
        *,
        document_key: str,
        title: str,
        text: str,
        revision: str,
        format: str,
        envelope: MutationEnvelope,
        require_lease: bool = True,
        tenant_id: str = "default",
    ) -> tuple[ProjectRecord, WorkflowRun]:
        project, run = super().ingest_script(
            document_key=document_key,
            title=title,
            text=text,
            revision=revision,
            format=format,
            envelope=envelope,
            require_lease=require_lease,
        )
        self._persist_project(project, tenant_id=tenant_id)
        return project, run

    def request_approval(
        self,
        *,
        document_key: str,
        kind: str,
        envelope: MutationEnvelope,
        target_ref: str | None = None,
    ) -> ApprovalRecord:
        record = super().request_approval(
            document_key=document_key,
            kind=kind,
            envelope=envelope,
            target_ref=target_ref,
        )
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO cf_approvals (approval_id, document_key, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (approval_id) DO UPDATE SET payload = EXCLUDED.payload
                """,
                (
                    str(record.approval_id),
                    document_key,
                    json.dumps(record.model_dump(mode="json")),
                ),
            )
            conn.commit()
        return record

    def record_approval(
        self,
        *,
        approval_id_value: UUID,
        status: ApprovalStatus,
        envelope: MutationEnvelope,
    ) -> ApprovalRecord:
        record = super().record_approval(
            approval_id_value=approval_id_value,
            status=status,
            envelope=envelope,
        )
        with _connect(self.dsn) as conn:
            conn.execute(
                """
                INSERT INTO cf_approvals (approval_id, document_key, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (approval_id) DO UPDATE SET payload = EXCLUDED.payload
                """,
                (
                    str(record.approval_id),
                    record.document_key,
                    json.dumps(record.model_dump(mode="json")),
                ),
            )
            conn.commit()
        return record
