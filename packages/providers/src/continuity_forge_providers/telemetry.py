"""Run-scoped cost / provider telemetry (not project canon).

Append-only cost events for a single proof or repair run. Mock workers emit
synthetic fixed-cost traces so offline UI and tests work without live keys.
Does not import ProjectStore; never elevates PROPOSED media.
"""

from __future__ import annotations

from typing import Any

from continuity_forge_ir import content_hash, stable_id
from pydantic import BaseModel, Field

from .contracts import ArtifactCandidate, Authority

# Synthetic fixed unit costs for offline / mock providers (USD).
# Zero-cost mock is intentional: no live billing in CI.
MOCK_PROVIDER_FIXED_COST: dict[str, float] = {
    "mock": 0.0,
}

# Default when provider is unknown but still PROPOSED.
DEFAULT_FIXED_COST = 0.0


class CostEvent(BaseModel):
    """One append-only generation attempt cost/trace record."""

    event_id: str
    sequence: int
    kind: str = "generate"
    shot_id: str
    attempt: int
    provider_id: str
    model: str
    seed: str | None = None
    latency_ms: float = 0.0
    estimated_cost: float | None = None
    authority: str = Authority.PROPOSED.value
    candidate_id: str | None = None
    candidate_hash: str | None = None
    is_retry: bool = False


class CostLedger(BaseModel):
    """Append-only cost ledger for a single run (provenance, not film state)."""

    claim: str = "cost_ledger_run_provenance_not_canon"
    events: list[CostEvent] = Field(default_factory=list)

    def append(self, event: CostEvent) -> CostLedger:
        """Return a new ledger with ``event`` appended (immutable-style)."""
        if any(e.event_id == event.event_id for e in self.events):
            # Idempotent: same event_id is ignored (no silent mutation).
            return self
        seq = len(self.events) + 1
        ordered = event.model_copy(update={"sequence": seq})
        return self.model_copy(update={"events": [*self.events, ordered]})

    def extend(self, events: list[CostEvent]) -> CostLedger:
        ledger = self
        for event in events:
            ledger = ledger.append(event)
        return ledger


class CostSummary(BaseModel):
    """Aggregate view over a cost ledger + optional wall-clock budget."""

    total_estimated_cost: float = 0.0
    event_count: int = 0
    by_provider: dict[str, int] = Field(default_factory=dict)
    cost_by_provider: dict[str, float] = Field(default_factory=dict)
    retry_event_count: int = 0
    retry_estimated_cost: float = 0.0
    wall_clock_seconds: float | None = None
    budget_seconds: float | None = None
    within_budget: bool | None = None
    authority_note: str = (
        "Cost ledger is run provenance only. PROPOSED candidates are never elevated. "
        "Not production film. Not a billing system."
    )


def fixed_cost_for_provider(provider_id: str) -> float:
    """Return synthetic fixed cost for a provider (mock → 0.0)."""
    key = (provider_id or "").casefold()
    if key in MOCK_PROVIDER_FIXED_COST:
        return MOCK_PROVIDER_FIXED_COST[key]
    return DEFAULT_FIXED_COST


def synthetic_latency_ms(*, seed: str, attempt: int, provider_id: str) -> float:
    """Deterministic synthetic latency for offline traces (1–50 ms band)."""
    digest = content_hash(f"{provider_id}:{seed}:{attempt}")
    return float((int(digest[:8], 16) % 50) + 1)


def event_from_candidate(
    candidate: ArtifactCandidate,
    *,
    attempt: int,
    sequence: int = 0,
    is_retry: bool = False,
    latency_ms: float | None = None,
    estimated_cost: float | None = None,
    kind: str = "generate",
) -> CostEvent:
    """Build a CostEvent from an ArtifactCandidate (always PROPOSED authority)."""
    provider_id = candidate.provider
    seed = candidate.seed
    cost = estimated_cost if estimated_cost is not None else fixed_cost_for_provider(provider_id)
    latency = (
        latency_ms
        if latency_ms is not None
        else synthetic_latency_ms(
            seed=seed or "0",
            attempt=attempt,
            provider_id=provider_id,
        )
    )
    event_id = str(
        stable_id(
            "cost",
            candidate.shot_id,
            attempt,
            provider_id,
            candidate.content_hash,
            kind,
        )
    )
    return CostEvent(
        event_id=event_id,
        sequence=sequence,
        kind=kind,
        shot_id=str(candidate.shot_id),
        attempt=attempt,
        provider_id=provider_id,
        model=candidate.model,
        seed=seed,
        latency_ms=latency,
        estimated_cost=cost,
        authority=Authority.PROPOSED.value,
        candidate_id=str(candidate.candidate_id),
        candidate_hash=candidate.content_hash,
        is_retry=is_retry,
    )


def summarize_ledger(
    ledger: CostLedger,
    *,
    wall_clock_seconds: float | None = None,
    budget_seconds: float | None = None,
) -> CostSummary:
    """Aggregate totals; wall-clock budget is independent of dollar cost."""
    by_provider: dict[str, int] = {}
    cost_by_provider: dict[str, float] = {}
    total = 0.0
    retry_count = 0
    retry_cost = 0.0
    for event in ledger.events:
        by_provider[event.provider_id] = by_provider.get(event.provider_id, 0) + 1
        ec = float(event.estimated_cost or 0.0)
        cost_by_provider[event.provider_id] = cost_by_provider.get(event.provider_id, 0.0) + ec
        total += ec
        if event.is_retry:
            retry_count += 1
            retry_cost += ec

    within: bool | None = None
    if wall_clock_seconds is not None and budget_seconds is not None:
        within = wall_clock_seconds <= budget_seconds

    return CostSummary(
        total_estimated_cost=round(total, 6),
        event_count=len(ledger.events),
        by_provider=dict(sorted(by_provider.items())),
        cost_by_provider={k: round(v, 6) for k, v in sorted(cost_by_provider.items())},
        retry_event_count=retry_count,
        retry_estimated_cost=round(retry_cost, 6),
        wall_clock_seconds=wall_clock_seconds,
        budget_seconds=budget_seconds,
        within_budget=within,
    )


def empty_ledger() -> CostLedger:
    return CostLedger()


def ledger_to_dict(ledger: CostLedger) -> dict[str, Any]:
    return ledger.model_dump(mode="json")
