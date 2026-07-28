"""OpenAI media worker — env-gated, injectable client for offline tests."""

from __future__ import annotations

import os
from typing import Any, Protocol

from continuity_forge_ir import content_hash, stable_id

from .contracts import ArtifactCandidate, Authority, WorkerTask


class OpenAIClient(Protocol):
    def generate_image(self, *, prompt: str, seed: str) -> dict[str, Any]: ...


class SdkOpenAIClient:
    """Real OpenAI SDK client (optional dependency)."""

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from openai import OpenAI  # type: ignore[import-not-found,unused-ignore]
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "openai package not installed. pip install 'continuity-forge[openai]'"
            ) from exc
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI worker")
        self._client = OpenAI(api_key=key)

    def generate_image(self, *, prompt: str, seed: str) -> dict[str, Any]:
        # Images API ignores seed on many models; we keep seed in provenance only.
        # size is env-driven; SDK types are Literal — cast via Any for env flexibility
        size: Any = os.environ.get("CF_OPENAI_IMAGE_SIZE", "1024x1024")
        result = self._client.images.generate(
            model=os.environ.get("CF_OPENAI_IMAGE_MODEL", "dall-e-3"),
            prompt=prompt[:3900],
            n=1,
            size=size,
        )
        data = result.data[0] if result.data else None
        url = getattr(data, "url", None) if data is not None else None
        b64 = getattr(data, "b64_json", None) if data is not None else None
        return {
            "provider": "openai",
            "model": os.environ.get("CF_OPENAI_IMAGE_MODEL", "dall-e-3"),
            "url": url,
            "b64_json": b64,
            "seed": seed,
        }


class OpenAIMediaWorker:
    """Generates PROPOSED image candidates via OpenAI (or an injected client)."""

    provider = "openai"
    model = "openai-images"

    def __init__(self, client: OpenAIClient | None = None) -> None:
        self._client = client

    def _client_or_raise(self) -> OpenAIClient:
        if self._client is not None:
            return self._client
        return SdkOpenAIClient()

    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask,
        seed: str,
    ) -> ArtifactCandidate:
        # OpenAI path is image-first; map video capability requests to stills.
        if task == WorkerTask.VIDEO:
            task = WorkerTask.IMAGE
        if task not in {WorkerTask.IMAGE, WorkerTask.VALIDATE}:
            raise RuntimeError(
                f"OpenAI worker does not support task={task.value}; use image/validate"
            )
        prompt = _prompt_from_shot(shot_contract)
        remote = self._client_or_raise().generate_image(prompt=prompt, seed=seed)
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
            "kind": "openai_media",
            "task": task.value,
            "seed": seed,
            "remote": {k: v for k, v in remote.items() if k != "b64_json"},
            "features": feature_bag,
        }
        digest = content_hash(repr(sorted(payload.items())))
        shot_id = __import__("uuid").UUID(str(shot_contract["shot_id"]))
        return ArtifactCandidate(
            candidate_id=stable_id("candidate", shot_id, "openai", seed, digest),
            shot_id=shot_id,
            task=task,
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


def _prompt_from_shot(shot_contract: dict[str, Any]) -> str:
    slug = shot_contract.get("slugline") or "scene"
    label = shot_contract.get("label") or ""
    hard = [
        str(c.get("description") or "")
        for c in shot_contract.get("constraints") or []
        if c.get("strength") == "hard"
    ][:12]
    return (
        f"Cinematic still for screenplay shot. Slugline: {slug}. Label: {label}. "
        f"Hard continuity constraints: {'; '.join(hard) or 'none'}."
    )
