"""Unit tests for run-scoped cost / provider telemetry (long-form 4.5)."""

from __future__ import annotations

from pathlib import Path

from continuity_forge_operator import ProjectStore
from continuity_forge_providers import (
    CostLedger,
    ProviderGateway,
    empty_ledger,
    event_from_candidate,
    fixed_cost_for_provider,
    summarize_ledger,
)
from continuity_forge_repair import run_repair_loop
from continuity_forge_repair.proof import run_controlled_proof

FIXTURE = Path(__file__).parents[1] / "golden" / "fixtures" / "continuity.fountain"


def test_mock_provider_fixed_cost_is_zero() -> None:
    assert fixed_cost_for_provider("mock") == 0.0
    assert fixed_cost_for_provider("MOCK") == 0.0


def test_cost_ledger_append_only_and_idempotent() -> None:
    gateway = ProviderGateway()
    contract = {
        "shot_id": "00000000-0000-4000-8000-000000000001",
        "scene_id": "00000000-0000-4000-8000-000000000002",
        "required_entity_ids": [],
        "constraints": [],
        "start_state_hash": "a",
        "end_state_hash": "b",
        "slugline": "INT. ROOM - DAY",
        "label": "master",
        "provider_capabilities": ["image"],
    }
    cand = gateway.generate_for_shot(contract, seed="0:1")
    e1 = event_from_candidate(cand, attempt=1, is_retry=False)
    e2 = event_from_candidate(
        gateway.generate_for_shot(contract, seed="0:2"),
        attempt=2,
        is_retry=True,
    )
    ledger = empty_ledger().append(e1).append(e2)
    assert len(ledger.events) == 2
    assert ledger.events[0].sequence == 1
    assert ledger.events[1].sequence == 2
    # Re-append same event_id does not mutate / reorder
    again = ledger.append(e1)
    assert len(again.events) == 2
    assert again.events[0].event_id == e1.event_id
    assert e1.authority == "PROPOSED"
    assert e1.estimated_cost == 0.0
    assert e1.provider_id == "mock"
    assert e1.model == "mock-media-v1"
    assert e1.candidate_hash
    assert e1.latency_ms >= 1.0


def test_summarize_includes_retry_and_budget() -> None:
    gateway = ProviderGateway()
    contract = {
        "shot_id": "00000000-0000-4000-8000-000000000010",
        "scene_id": "00000000-0000-4000-8000-000000000011",
        "required_entity_ids": [],
        "constraints": [],
        "start_state_hash": "a",
        "end_state_hash": "b",
        "provider_capabilities": ["image"],
    }
    c1 = gateway.generate_for_shot(contract, seed="s:1")
    c2 = gateway.generate_for_shot(contract, seed="s:2")
    ledger = (
        empty_ledger()
        .append(event_from_candidate(c1, attempt=1, is_retry=False))
        .append(event_from_candidate(c2, attempt=2, is_retry=True))
    )
    summary = summarize_ledger(ledger, wall_clock_seconds=1.5, budget_seconds=60.0)
    assert summary.event_count == 2
    assert summary.by_provider.get("mock") == 2
    assert summary.retry_event_count == 1
    assert summary.within_budget is True
    assert summary.total_estimated_cost == 0.0
    assert "PROPOSED" in summary.authority_note or "canon" in summary.authority_note.lower()


def test_repair_loop_emits_cost_events() -> None:
    contract = {
        "shot_id": "00000000-0000-4000-8000-000000000020",
        "scene_id": "00000000-0000-4000-8000-000000000021",
        "required_entity_ids": ["00000000-0000-4000-8000-000000000099"],
        "constraints": [],
        "start_state_hash": "a",
        "end_state_hash": "b",
        "provider_capabilities": ["image"],
    }
    # force fail_first needs entities in feature bag from mock — use real-shaped via proof path
    result = run_repair_loop(contract, seed="t", fail_first=True, max_attempts=3)
    assert result.cost_events
    assert len(result.cost_events) == len(result.attempts)
    assert result.cost_events[0].is_retry is False
    if len(result.cost_events) > 1:
        assert result.cost_events[1].is_retry is True
    assert all(e.authority == "PROPOSED" for e in result.cost_events)


def test_proof_receipt_includes_cost_ledger_and_summary() -> None:
    receipt = run_controlled_proof(
        FIXTURE,
        store=ProjectStore(),
        document_key="cost-proof",
        seed="c",
        budget_seconds=60.0,
    )
    assert receipt.cost_ledger is not None
    assert receipt.cost_summary is not None
    assert receipt.cost_ledger.claim == "cost_ledger_run_provenance_not_canon"
    assert receipt.cost_summary.event_count >= len(receipt.shots)
    # fail_first on first shot → at least one retry event across the run
    assert receipt.cost_summary.retry_event_count >= 1
    assert receipt.cost_summary.within_budget is receipt.within_budget
    assert receipt.cost_summary.by_provider.get("mock", 0) == receipt.cost_summary.event_count
    assert all(e.authority == "PROPOSED" for e in receipt.cost_ledger.events)
    # Append-only sequences are dense 1..n
    seqs = [e.sequence for e in receipt.cost_ledger.events]
    assert seqs == list(range(1, len(seqs) + 1))


def test_cost_ledger_does_not_import_project_store() -> None:
    import continuity_forge_providers.telemetry as tel

    source = Path(tel.__file__).read_text(encoding="utf-8")
    assert "from continuity_forge_operator" not in source
    assert "import continuity_forge_operator" not in source
    # Type exists and is pure
    assert CostLedger is not None
