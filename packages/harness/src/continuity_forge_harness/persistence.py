"""Filesystem-backed workflow run store."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from uuid import UUID

from .models import WorkflowRun
from .store import RunStore


class FileRunStore(RunStore):
    """Persists workflow runs as JSON files under a root directory."""

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / "index.json"
        self._file_lock = RLock()
        self._load()

    def _load(self) -> None:
        if not self._index_path.exists():
            return
        payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        for raw in payload.get("runs", []):
            run = WorkflowRun.model_validate(raw)
            # Bypass put validation during bootstrap.
            self._by_id[run.run_id] = run
            self._by_idempotency[run.idempotency_key] = run.run_id

    def _flush(self) -> None:
        runs = [run.model_dump(mode="json") for run in self._by_id.values()]
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"runs": runs}, indent=2), encoding="utf-8")
        tmp.replace(self._index_path)

    def put(self, run: WorkflowRun) -> WorkflowRun:
        with self._file_lock:
            stored = super().put(run)
            self._flush()
            return stored

    def get(self, run_id: UUID) -> WorkflowRun | None:
        with self._file_lock:
            return super().get(run_id)

    def get_by_idempotency(self, idempotency_key: str) -> WorkflowRun | None:
        with self._file_lock:
            return super().get_by_idempotency(idempotency_key)

    def list_runs(self) -> list[WorkflowRun]:
        with self._file_lock:
            return super().list_runs()
