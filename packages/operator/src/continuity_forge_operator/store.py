"""In-process project operator store with write leases."""

from __future__ import annotations

from datetime import timedelta
from threading import RLock
from uuid import UUID

from continuity_forge_harness import (
    DEFAULT_RUN_STORE,
    PipelineCommand,
    RunStore,
    WorkflowRun,
    execute_kernel_pipeline,
)
from continuity_forge_ir import content_hash

from .models import (
    ApprovalRecord,
    ApprovalStatus,
    MutationEnvelope,
    ProjectRecord,
    WriteLease,
    approval_id,
    project_state_hash,
    utc_now,
)


class OperatorError(RuntimeError):
    pass


class ProjectStore:
    def __init__(self, run_store: RunStore | None = None) -> None:
        self._projects: dict[str, ProjectRecord] = {}
        self._leases: dict[str, WriteLease] = {}
        self._approvals: dict[UUID, ApprovalRecord] = {}
        self._artifacts: dict[str, dict[str, object]] = {}
        self._lock = RLock()
        self._runs = run_store or DEFAULT_RUN_STORE

    def get_project(self, document_key: str) -> ProjectRecord | None:
        with self._lock:
            project = self._projects.get(document_key)
            return project.model_copy(deep=True) if project else None

    def list_projects(self) -> list[ProjectRecord]:
        with self._lock:
            return [p.model_copy(deep=True) for p in self._projects.values()]

    def acquire_lease(
        self,
        document_key: str,
        holder: str,
        *,
        scope: str = "project",
        ttl_seconds: int = 300,
    ) -> WriteLease:
        with self._lock:
            now = utc_now()
            current = self._leases.get(document_key)
            if current and current.is_active(now) and current.holder != holder:
                raise OperatorError(
                    f"write lease held by {current.holder} until {current.expires_at.isoformat()}"
                )
            lease = WriteLease(
                document_key=document_key,
                holder=holder,
                scope=scope,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            self._leases[document_key] = lease
            return lease.model_copy(deep=True)

    def release_lease(self, document_key: str, holder: str) -> None:
        with self._lock:
            current = self._leases.get(document_key)
            if current is None:
                return
            if current.holder != holder:
                raise OperatorError("only the lease holder may release the write lease")
            del self._leases[document_key]

    def get_lease(self, document_key: str) -> WriteLease | None:
        with self._lock:
            current = self._leases.get(document_key)
            return current.model_copy(deep=True) if current else None

    def _require_lease(self, document_key: str, actor_id: str) -> None:
        current = self._leases.get(document_key)
        now = utc_now()
        if current is None or not current.is_active(now):
            raise OperatorError("active write lease required for mutation")
        if current.holder != actor_id:
            raise OperatorError("actor does not hold the write lease")

    def _check_expected_project_state(self, document_key: str, envelope: MutationEnvelope) -> None:
        """Optimistic concurrency against ProjectRecord.state_hash.

        ``MutationEnvelope.expected_state_hash`` is the project state domain
        (see ``project_state_hash``), not pipeline ``shot_contracts_hash``.
        """
        existing = self._projects.get(document_key)
        if existing is None or existing.state_hash is None:
            return
        if envelope.expected_state_hash is None:
            raise OperatorError("expected_state_hash required when continuing prior project state")
        if envelope.expected_state_hash != existing.state_hash:
            raise OperatorError(
                "expected_state_hash conflict: does not match current project state_hash"
            )

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
        with self._lock:
            if require_lease:
                self._require_lease(document_key, envelope.actor_id)
            self._check_expected_project_state(document_key, envelope)
            # Project-level expected_state_hash is enforced above. PipelineCommand
            # expected_state_hash is a separate domain (shot_contracts_hash) used
            # only on direct pipeline runs — do not forward project state_hash.
            command = PipelineCommand(
                actor_id=envelope.actor_id,
                authorization_scope=envelope.authorization_scope,
                idempotency_key=envelope.idempotency_key,
                rationale=envelope.rationale,
                expected_state_hash=None,
                title=title,
                text=text,
                revision=revision,
                document_key=document_key,
                format=format,  # type: ignore[arg-type]
            )
        run = execute_kernel_pipeline(command, store=self._runs)
        if run.artifacts is None:
            raise OperatorError(run.error or "pipeline produced no artifacts")
        project = ProjectRecord(
            document_key=document_key,
            title=title,
            source_text=text,
            source_hash=content_hash(text),
            revision=revision,
            format=format,
            updated_at=utc_now(),
            production_ir=run.artifacts.production_ir,
            continuity_ledger=run.artifacts.continuity_ledger,
            shot_contracts=run.artifacts.shot_contracts,
            last_pipeline_run_id=run.run_id,
        )
        project = project.model_copy(update={"state_hash": project_state_hash(project)})
        with self._lock:
            self._projects[document_key] = project
            if run.artifacts.production_ir_hash:
                self._artifacts[run.artifacts.production_ir_hash] = run.artifacts.production_ir
            if run.artifacts.ledger_hash:
                self._artifacts[run.artifacts.ledger_hash] = run.artifacts.continuity_ledger
            if run.artifacts.shot_contracts_hash:
                self._artifacts[run.artifacts.shot_contracts_hash] = run.artifacts.shot_contracts
        return project.model_copy(deep=True), run

    def request_approval(
        self,
        *,
        document_key: str,
        kind: str,
        envelope: MutationEnvelope,
        target_ref: str | None = None,
    ) -> ApprovalRecord:
        with self._lock:
            self._require_lease(document_key, envelope.actor_id)
            if document_key not in self._projects:
                raise OperatorError("unknown project")
            record = ApprovalRecord(
                approval_id=approval_id(document_key, kind, envelope.idempotency_key),
                document_key=document_key,
                kind=kind,
                status=ApprovalStatus.REQUESTED,
                actor_id=envelope.actor_id,
                rationale=envelope.rationale,
                created_at=utc_now(),
                target_ref=target_ref,
            )
            self._approvals[record.approval_id] = record
            return record.model_copy(deep=True)

    def record_approval(
        self,
        *,
        approval_id_value: UUID,
        status: ApprovalStatus,
        envelope: MutationEnvelope,
    ) -> ApprovalRecord:
        with self._lock:
            record = self._approvals.get(approval_id_value)
            if record is None:
                raise OperatorError("unknown approval")
            self._require_lease(record.document_key, envelope.actor_id)
            if status not in {ApprovalStatus.GRANTED, ApprovalStatus.DENIED}:
                raise OperatorError("status must be granted or denied")
            updated = record.model_copy(
                update={
                    "status": status,
                    "actor_id": envelope.actor_id,
                    "rationale": envelope.rationale,
                }
            )
            self._approvals[approval_id_value] = updated
            return updated.model_copy(deep=True)

    def list_approvals(self, document_key: str) -> list[ApprovalRecord]:
        with self._lock:
            return [
                a.model_copy(deep=True)
                for a in self._approvals.values()
                if a.document_key == document_key
            ]

    def list_runs_for_project(self, document_key: str) -> list[WorkflowRun]:
        return [run for run in self._runs.list_runs() if run.command.document_key == document_key]

    def resource(self, uri: str) -> dict[str, object] | None:
        """Resolve cf:// resource URIs to JSON payloads."""
        if not uri.startswith("cf://"):
            return None
        path = uri[len("cf://") :].strip("/")
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "projects":
            document_key, kind = parts[1], parts[2]
            project = self.get_project(document_key)
            if project is None:
                return None
            if kind == "script":
                return {
                    "document_key": document_key,
                    "title": project.title,
                    "source_hash": project.source_hash,
                    "revision": project.revision,
                    "format": project.format,
                    "text": project.source_text,
                }
            if kind == "production-ir":
                return project.production_ir
            if kind == "continuity-ledger":
                return project.continuity_ledger
            if kind == "coverage-report":
                ir = project.production_ir or {}
                return ir.get("coverage")
            if kind == "status":
                return {
                    "document_key": document_key,
                    "title": project.title,
                    "revision": project.revision,
                    "source_hash": project.source_hash,
                    "state_hash": project.state_hash,
                    "last_pipeline_run_id": str(project.last_pipeline_run_id)
                    if project.last_pipeline_run_id
                    else None,
                    "scene_count": len((project.production_ir or {}).get("scenes") or []),
                    "shot_count": len((project.shot_contracts or {}).get("contracts") or []),
                }
        if len(parts) >= 3 and parts[0] == "scenes" and parts[2] == "manifest":
            scene_id = parts[1]
            for project in self.list_projects():
                scenes = (project.production_ir or {}).get("scenes") or []
                contracts = (project.shot_contracts or {}).get("contracts") or []
                scene = next((s for s in scenes if s.get("scene_id") == scene_id), None)
                if scene is None:
                    continue
                contract = next((c for c in contracts if c.get("scene_id") == scene_id), None)
                return {
                    "document_key": project.document_key,
                    "scene": scene,
                    "shot_contract": contract,
                }
        if len(parts) >= 3 and parts[0] == "shots" and parts[2] == "validation":
            shot_id = parts[1]
            for project in self.list_projects():
                contracts = (project.shot_contracts or {}).get("contracts") or []
                contract = next((c for c in contracts if c.get("shot_id") == shot_id), None)
                if contract is None:
                    continue
                return {
                    "document_key": project.document_key,
                    "shot_id": shot_id,
                    "validation_checks": contract.get("validation_checks"),
                    "constraints": contract.get("constraints"),
                    "start_state_hash": contract.get("start_state_hash"),
                    "end_state_hash": contract.get("end_state_hash"),
                }
        return None


DEFAULT_PROJECT_STORE = ProjectStore()
