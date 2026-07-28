"""Content-addressed local artifact store (S3-shaped; filesystem for now)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock
from typing import Any

from continuity_forge_ir import content_hash

from .contracts import ArtifactCandidate


class ArtifactStore:
    """Store artifact candidates by content hash under a root directory."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index = self.root / "index.json"
        self._lock = RLock()
        self._by_hash: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._index.exists():
            return
        data = json.loads(self._index.read_text(encoding="utf-8"))
        self._by_hash = {item["content_hash"]: item for item in data.get("artifacts", [])}

    def _flush(self) -> None:
        payload = {"artifacts": list(self._by_hash.values())}
        tmp = self._index.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self._index)

    def put(self, candidate: ArtifactCandidate) -> str:
        """Persist candidate JSON; returns content hash."""
        body = candidate.model_dump(mode="json")
        digest = candidate.content_hash or content_hash(json.dumps(body, sort_keys=True))
        blob_path = self.root / "blobs" / f"{digest}.json"
        with self._lock:
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            blob_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
            self._by_hash[digest] = {
                "content_hash": digest,
                "candidate_id": str(candidate.candidate_id),
                "shot_id": str(candidate.shot_id),
                "provider": candidate.provider,
                "path": str(blob_path.relative_to(self.root)),
                "authority": candidate.authority.value,
            }
            self._flush()
        return digest

    def get(self, content_hash_value: str) -> dict[str, Any] | None:
        with self._lock:
            meta = self._by_hash.get(content_hash_value)
            if meta is None:
                return None
            path = self.root / str(meta["path"])
            if not path.exists():
                return None
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                return None
            return {str(k): v for k, v in loaded.items()}

    def list_hashes(self) -> list[str]:
        with self._lock:
            return sorted(self._by_hash)
