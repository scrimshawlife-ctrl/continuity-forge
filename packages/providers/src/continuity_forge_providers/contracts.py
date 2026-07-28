from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id
from pydantic import BaseModel, Field


class Authority(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class WorkerTask(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    VALIDATE = "validate"


class ModelRequest(BaseModel):
    task: str
    input: dict[str, Any]
    schema_name: str | None = None


class ModelResult(BaseModel):
    provider: str
    model: str
    output: dict[str, Any]
    authority: str = Authority.PROPOSED.value


class ModelGateway(Protocol):
    async def execute(self, request: ModelRequest) -> ModelResult: ...


class ArtifactCandidate(BaseModel):
    candidate_id: UUID
    shot_id: UUID
    task: WorkerTask
    provider: str
    model: str
    seed: str
    authority: Authority = Authority.PROPOSED
    content_hash: str
    feature_bag: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, str] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)


class MediaWorker(Protocol):
    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask,
        seed: str,
    ) -> ArtifactCandidate: ...


class MockMediaWorker:
    """Deterministic offline worker. Never mutates kernel state."""

    provider = "mock"
    model = "mock-media-v1"

    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask = WorkerTask.IMAGE,
        seed: str = "0",
        force_missing_entities: bool = False,
    ) -> ArtifactCandidate:
        shot_id = UUID(str(shot_contract["shot_id"]))
        entity_ids = [str(e) for e in shot_contract.get("required_entity_ids") or []]
        if force_missing_entities:
            entity_ids = entity_ids[: max(0, len(entity_ids) - 1)]
        prohibited = [
            str(c.get("entity_id"))
            for c in shot_contract.get("constraints") or []
            if c.get("code") == "forbid_prop" and c.get("entity_id")
        ]
        feature_bag = {
            "entity_ids": entity_ids,
            "prohibited_seen": [],
            "start_state_hash": shot_contract.get("start_state_hash"),
            "end_state_hash": shot_contract.get("end_state_hash"),
            "slugline": shot_contract.get("slugline"),
            "label": shot_contract.get("label"),
        }
        payload = {
            "kind": "mock_media",
            "task": task.value,
            "seed": seed,
            "shot_id": str(shot_id),
            "features": feature_bag,
            "prohibited_reference": prohibited,
        }
        digest = content_hash(repr(sorted(payload.items())))
        candidate_id = stable_id("candidate", shot_id, task.value, seed, digest)
        return ArtifactCandidate(
            candidate_id=candidate_id,
            shot_id=shot_id,
            task=task,
            provider=self.provider,
            model=self.model,
            seed=seed,
            authority=Authority.PROPOSED,
            content_hash=digest,
            feature_bag=feature_bag,
            lineage={
                "shot_id": str(shot_id),
                "start_state_hash": str(shot_contract.get("start_state_hash") or ""),
                "end_state_hash": str(shot_contract.get("end_state_hash") or ""),
            },
            payload=payload,
        )


class ProviderGateway:
    """Routes shot capabilities to isolated mock workers."""

    def __init__(self, worker: MediaWorker | None = None) -> None:
        self._worker = worker or MockMediaWorker()

    def generate_for_shot(
        self,
        shot_contract: dict[str, Any],
        *,
        seed: str = "0",
        task: WorkerTask | None = None,
        force_missing_entities: bool = False,
    ) -> ArtifactCandidate:
        capabilities = shot_contract.get("provider_capabilities") or ["image"]
        resolved = task or (
            WorkerTask.VIDEO
            if "video" in capabilities
            else WorkerTask.IMAGE
            if "image" in capabilities
            else WorkerTask.VALIDATE
        )
        if isinstance(self._worker, MockMediaWorker):
            return self._worker.generate(
                shot_contract=shot_contract,
                task=resolved,
                seed=seed,
                force_missing_entities=force_missing_entities,
            )
        return self._worker.generate(shot_contract=shot_contract, task=resolved, seed=seed)
