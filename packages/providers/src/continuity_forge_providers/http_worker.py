"""Env-gated HTTP media worker for real provider gateways.

Default behavior is dry-run (delegates to MockMediaWorker) unless
CF_PROVIDER_HTTP_URL is set and CF_PROVIDER_DRY_RUN is not truthy.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from .contracts import ArtifactCandidate, MockMediaWorker, WorkerTask


class HttpTransport(Protocol):
    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class HttpxTransport:
    """Thin httpx wrapper (imported lazily so httpx remains a dev/runtime choice)."""

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        response = httpx.post(url, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise TypeError("provider HTTP response must be a JSON object")
        return data


class HttpMediaWorker:
    """POST shot contracts to an external provider HTTP endpoint."""

    provider = "http"
    model = "http-gateway-v1"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        transport: HttpTransport | None = None,
        dry_run: bool | None = None,
        fallback: MockMediaWorker | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("CF_PROVIDER_HTTP_URL") or "").rstrip("/")
        env_dry = os.environ.get("CF_PROVIDER_DRY_RUN", "").casefold() in {"1", "true", "yes"}
        self.dry_run = env_dry if dry_run is None else dry_run
        self.transport = transport or HttpxTransport()
        self.fallback = fallback or MockMediaWorker()

    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask,
        seed: str,
    ) -> ArtifactCandidate:
        if self.dry_run or not self.base_url:
            candidate = self.fallback.generate(shot_contract=shot_contract, task=task, seed=seed)
            return candidate.model_copy(
                update={
                    "provider": self.provider if self.base_url else "mock",
                    "model": (f"{self.model}+dry-run" if self.base_url else self.fallback.model),
                }
            )

        url = f"{self.base_url}/v1/generate"
        payload = {
            "task": task.value,
            "seed": seed,
            "shot_contract": shot_contract,
        }
        body = self.transport.post_json(url, payload)
        # Accept either a full ArtifactCandidate dict or a minimal envelope.
        if "candidate_id" in body and "content_hash" in body:
            return ArtifactCandidate.model_validate(body)
        # Wrap opaque provider payload as PROPOSED candidate via mock shell + merge.
        base = self.fallback.generate(shot_contract=shot_contract, task=task, seed=seed)
        return base.model_copy(
            update={
                "provider": str(body.get("provider") or self.provider),
                "model": str(body.get("model") or self.model),
                "payload": {**base.payload, "remote": body},
                "authority": base.authority,
            }
        )
