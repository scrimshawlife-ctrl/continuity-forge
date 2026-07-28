"""In-process durable run store with idempotency (M3)."""

from __future__ import annotations

from threading import RLock
from uuid import UUID

from .models import WorkflowRun


class RunStore:
    """Thread-safe in-memory store keyed by idempotency key and run ID."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, WorkflowRun] = {}
        self._by_idempotency: dict[str, UUID] = {}
        self._lock = RLock()

    def get(self, run_id: UUID) -> WorkflowRun | None:
        with self._lock:
            run = self._by_id.get(run_id)
            return run.model_copy(deep=True) if run is not None else None

    def get_by_idempotency(self, idempotency_key: str) -> WorkflowRun | None:
        with self._lock:
            run_id = self._by_idempotency.get(idempotency_key)
            if run_id is None:
                return None
            return self.get(run_id)

    def put(self, run: WorkflowRun) -> WorkflowRun:
        with self._lock:
            existing_id = self._by_idempotency.get(run.idempotency_key)
            if existing_id is not None and existing_id != run.run_id:
                raise ValueError("idempotency key already bound to a different run")
            self._by_id[run.run_id] = run.model_copy(deep=True)
            self._by_idempotency[run.idempotency_key] = run.run_id
            return run.model_copy(deep=True)

    def list_runs(self) -> list[WorkflowRun]:
        with self._lock:
            return [run.model_copy(deep=True) for run in self._by_id.values()]


# Process-local default store for API/MCP in M3.
DEFAULT_RUN_STORE = RunStore()
