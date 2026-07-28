"""Provider registry — mock default, fail-closed real slots."""

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
        raise RuntimeError(
            f"Provider '{self.name}' is not configured. Set {self.env_var} or use provider=mock."
        )


_REGISTRY: dict[str, MediaWorker] = {
    "mock": MockMediaWorker(),
    "openai": UnconfiguredRealWorker("openai", "OPENAI_API_KEY"),
    "runway": UnconfiguredRealWorker("runway", "RUNWAY_API_KEY"),
}


def list_providers() -> list[str]:
    return sorted(_REGISTRY)


def get_worker(name: str | None = None) -> MediaWorker:
    selected = (name or os.environ.get("CF_PROVIDER") or "mock").casefold()
    if selected not in _REGISTRY:
        raise KeyError(f"unknown provider '{selected}'; known={list_providers()}")
    return _REGISTRY[selected]


def get_gateway(name: str | None = None) -> ProviderGateway:
    return ProviderGateway(worker=get_worker(name))


def register_worker(name: str, worker: MediaWorker) -> None:
    _REGISTRY[name.casefold()] = worker
