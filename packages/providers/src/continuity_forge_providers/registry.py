"""Provider registry — mock default, fail-closed real slots, HTTP gateway."""

from __future__ import annotations

import os
from typing import Any

from .contracts import (
    ArtifactCandidate,
    MediaWorker,
    MockMediaWorker,
    ProviderGateway,
    WorkerTask,
)
from .http_worker import HttpMediaWorker


class UnconfiguredRealWorker:
    """Fail-closed placeholder for a real provider until credentials exist."""

    provider: str
    model: str = "none"

    def __init__(self, name: str, env_var: str) -> None:
        self.provider = name
        self.name = name
        self.env_var = env_var

    def generate(
        self,
        *,
        shot_contract: dict[str, Any],
        task: WorkerTask,
        seed: str,
    ) -> ArtifactCandidate:
        if not os.environ.get(self.env_var):
            raise RuntimeError(
                f"Provider '{self.name}' is not configured. "
                f"Set {self.env_var} or use provider=mock."
            )
        # Credential present but SDK not wired yet — still fail closed with guidance.
        raise RuntimeError(
            f"Provider '{self.name}' credentials detected via {self.env_var}, "
            "but the SDK adapter is not implemented yet. Use provider=http with "
            "CF_PROVIDER_HTTP_URL for a custom gateway, or provider=mock."
        )


def _build_registry() -> dict[str, MediaWorker]:
    return {
        "mock": MockMediaWorker(),
        "http": HttpMediaWorker(),
        "openai": UnconfiguredRealWorker("openai", "OPENAI_API_KEY"),
        "runway": UnconfiguredRealWorker("runway", "RUNWAY_API_KEY"),
    }


_REGISTRY: dict[str, MediaWorker] = _build_registry()


def list_providers() -> list[str]:
    return sorted(_REGISTRY)


def get_worker(name: str | None = None) -> MediaWorker:
    selected = (name or os.environ.get("CF_PROVIDER") or "mock").casefold()
    if selected not in _REGISTRY:
        raise KeyError(f"unknown provider '{selected}'; known={list_providers()}")
    # Rebuild http worker each time so env changes apply.
    if selected == "http":
        return HttpMediaWorker()
    return _REGISTRY[selected]


def get_gateway(name: str | None = None) -> ProviderGateway:
    return ProviderGateway(worker=get_worker(name))


def register_worker(name: str, worker: MediaWorker) -> None:
    _REGISTRY[name.casefold()] = worker
