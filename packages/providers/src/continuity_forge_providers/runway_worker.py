"""Runway media worker — env-gated HTTP API with injectable transport."""

from __future__ import annotations

import os
from typing import Any, Protocol
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id

from .contracts import ArtifactCandidate, Authority, WorkerTask


class RunwayTransport(Protocol):
    def create_generation(self, *, payload: dict[str, Any]) -> dict[str, Any]: ...


class HttpRunwayTransport:
    """Minimal Runway-compatible REST transport via httpx."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("RUNWAY_API_KEY")
        if not self.api_key:
            raise RuntimeError("RUNWAY_API_KEY is required for the Runway worker")
        self.base_url = (
            base_url or os.environ.get("CF_RUNWAY_BASE_URL") or "https://api.dev.runwayml.com"
        ).rstrip("/")

    def create_generation(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": os.environ.get("CF_RUNWAY_VERSION", "2024-11-06"),
        }
        response = httpx.post(
            f"{self.base_url}/v1/image_to_video",
            headers=headers,
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("Runway response must be a JSON object")
        return data


class RunwayMediaWorker:
    """Generates PROPOSED video candidates via Runway (or injected transport)."""

    provider = "runway"
    model = "runway-gen"

    def __init__(self, transport: RunwayTransport | None = None) -> None:
        self._transport = transport

    def _transport_or_raise(self) -> RunwayTransport:
        if self._transport is not None:
            return self._transport
        return HttpRunwayTransport()

    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask,
        seed: str,
    ) -> ArtifactCandidate:
        if task not in {WorkerTask.VIDEO, WorkerTask.IMAGE, WorkerTask.VALIDATE}:
            raise RuntimeError(f"Runway worker does not support task={task.value}")
        prompt = (
            f"{shot_contract.get('slugline') or 'scene'} — "
            f"{shot_contract.get('label') or 'master shot'}"
        )
        remote = self._transport_or_raise().create_generation(
            payload={
                "promptText": prompt[:1000],
                "seed": abs(hash(seed)) % (2**31),
                "model": os.environ.get("CF_RUNWAY_MODEL", "gen3a_turbo"),
                "duration": int(os.environ.get("CF_RUNWAY_DURATION", "5")),
            }
        )
        model = str(remote.get("model") or self.model)
        entity_ids = [str(e) for e in shot_contract.get("required_entity_ids") or []]
        feature_bag = {
            "entity_ids": entity_ids,
            "prohibited_seen": [],
            "start_state_hash": shot_contract.get("start_state_hash"),
            "end_state_hash": shot_contract.get("end_state_hash"),
            "slugline": shot_contract.get("slugline"),
            "prompt": prompt,
        }
        payload = {
            "kind": "runway_media",
            "task": task.value,
            "seed": seed,
            "remote": remote,
            "features": feature_bag,
        }
        digest = content_hash(repr(sorted(payload.items())))
        shot_id = UUID(str(shot_contract["shot_id"]))
        return ArtifactCandidate(
            candidate_id=stable_id("candidate", shot_id, "runway", seed, digest),
            shot_id=shot_id,
            task=task if task != WorkerTask.VALIDATE else WorkerTask.VIDEO,
            provider=self.provider,
            model=model,
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
