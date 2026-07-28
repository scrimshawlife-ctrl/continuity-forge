"""Filesystem-backed project operator store."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from uuid import UUID

from continuity_forge_harness import FileRunStore, RunStore, WorkflowRun

from .models import (
    ApprovalRecord,
    ApprovalStatus,
    MutationEnvelope,
    ProjectRecord,
    WriteLease,
)
from .store import ProjectStore


class FileProjectStore(ProjectStore):
    """Persists projects, leases, and approvals under a root directory."""

    def __init__(self, root: Path, run_store: RunStore | None = None) -> None:
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        runs = run_store or FileRunStore(root / "runs")
        super().__init__(run_store=runs)
        self.root = root
        self._projects_path = root / "projects.json"
        self._leases_path = root / "leases.json"
        self._approvals_path = root / "approvals.json"
        self._persist_lock = RLock()
        self._load()

    def _load(self) -> None:
        if self._projects_path.exists():
            data = json.loads(self._projects_path.read_text(encoding="utf-8"))
            for raw in data.get("projects", []):
                project = ProjectRecord.model_validate(raw)
                self._projects[project.document_key] = project
        if self._leases_path.exists():
            data = json.loads(self._leases_path.read_text(encoding="utf-8"))
            for raw in data.get("leases", []):
                lease = WriteLease.model_validate(raw)
                self._leases[lease.document_key] = lease
        if self._approvals_path.exists():
            data = json.loads(self._approvals_path.read_text(encoding="utf-8"))
            for raw in data.get("approvals", []):
                approval = ApprovalRecord.model_validate(raw)
                self._approvals[approval.approval_id] = approval

    def _flush(self) -> None:
        with self._persist_lock:
            self._projects_path.write_text(
                json.dumps(
                    {"projects": [p.model_dump(mode="json") for p in self._projects.values()]},
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._leases_path.write_text(
                json.dumps(
                    {"leases": [lease.model_dump(mode="json") for lease in self._leases.values()]},
                    indent=2,
                ),
                encoding="utf-8",
            )
            self._approvals_path.write_text(
                json.dumps(
                    {"approvals": [a.model_dump(mode="json") for a in self._approvals.values()]},
                    indent=2,
                ),
                encoding="utf-8",
            )

    def acquire_lease(
        self,
        document_key: str,
        holder: str,
        *,
        scope: str = "project",
        ttl_seconds: int = 300,
    ) -> WriteLease:
        lease = super().acquire_lease(document_key, holder, scope=scope, ttl_seconds=ttl_seconds)
        self._flush()
        return lease

    def release_lease(self, document_key: str, holder: str) -> None:
        super().release_lease(document_key, holder)
        self._flush()

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
    ) -> tuple[ProjectRecord, WorkflowRun]:
        result = super().ingest_script(
            document_key=document_key,
            title=title,
            text=text,
            revision=revision,
            format=format,
            envelope=envelope,
            require_lease=require_lease,
        )
        self._flush()
        return result

    def request_approval(
        self,
        *,
        document_key: str,
        kind: str,
        envelope: MutationEnvelope,
        target_ref: str | None = None,
    ) -> ApprovalRecord:
        result = super().request_approval(
            document_key=document_key,
            kind=kind,
            envelope=envelope,
            target_ref=target_ref,
        )
        self._flush()
        return result

    def record_approval(
        self,
        *,
        approval_id_value: UUID,
        status: ApprovalStatus,
        envelope: MutationEnvelope,
    ) -> ApprovalRecord:
        result = super().record_approval(
            approval_id_value=approval_id_value,
            status=status,
            envelope=envelope,
        )
        self._flush()
        return result
