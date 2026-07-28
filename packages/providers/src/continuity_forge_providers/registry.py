"""Provider registry — mock default, HTTP, OpenAI, Runway."""

from __future__ import annotations

import os

from .contracts import MediaWorker, MockMediaWorker, ProviderGateway
from .http_worker import HttpMediaWorker
from .openai_worker import OpenAIMediaWorker
from .runway_worker import RunwayMediaWorker


def _build_registry() -> dict[str, MediaWorker]:
    return {
        "mock": MockMediaWorker(),
        "http": HttpMediaWorker(),
        "openai": OpenAIMediaWorker(),
        "runway": RunwayMediaWorker(),
    }


_REGISTRY: dict[str, MediaWorker] = _build_registry()


def list_providers() -> list[str]:
    return sorted(_REGISTRY)


def get_worker(name: str | None = None) -> MediaWorker:
    selected = (name or os.environ.get("CF_PROVIDER") or "mock").casefold()
    if selected not in _REGISTRY:
        raise KeyError(f"unknown provider '{selected}'; known={list_providers()}")
    # Rebuild env-sensitive workers each call.
    if selected == "http":
        return HttpMediaWorker()
    if selected == "openai":
        return OpenAIMediaWorker()
    if selected == "runway":
        return RunwayMediaWorker()
    return _REGISTRY[selected]


def get_gateway(name: str | None = None) -> ProviderGateway:
    return ProviderGateway(worker=get_worker(name))


def register_worker(name: str, worker: MediaWorker) -> None:
    _REGISTRY[name.casefold()] = worker
