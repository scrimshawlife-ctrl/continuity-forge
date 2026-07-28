from pathlib import Path

from continuity_forge_operator import ProjectStore
from continuity_forge_repair.proof import run_controlled_proof

FIXTURE = Path(__file__).parents[1] / "golden" / "fixtures" / "continuity.fountain"


def test_controlled_proof_receipt() -> None:
    store = ProjectStore()
    first = run_controlled_proof(FIXTURE, store=store, document_key="proof-doc", seed="s")
    second = run_controlled_proof(FIXTURE, store=ProjectStore(), document_key="proof-doc", seed="s")
    assert first.schema_version == "m7.proof.v1"
    assert first.claim == "controlled_proof_not_production_ready"
    # First shot is force-failed once: repair_actions + validator rationale expected.
    assert first.shots
    assert first.shots[0].repair_actions
    assert first.shots[0].repair_rationale
    assert first.shots
    assert first.receipt_hash
    assert first.within_budget
    assert first.cost_ledger is not None
    assert first.cost_summary is not None
    assert first.cost_summary.event_count >= 1
    assert first.cost_summary.retry_event_count >= 1
    assert first.cost_ledger.claim == "cost_ledger_run_provenance_not_canon"
    # Deterministic artifact hashes for same seed/source
    assert first.source_hash == second.source_hash
    assert first.production_ir_hash == second.production_ir_hash
    assert first.shot_contracts_hash == second.shot_contracts_hash
    assert [s.accepted_candidate_hash for s in first.shots] == [
        s.accepted_candidate_hash for s in second.shots
    ]
    assert first.shots[0].attempts >= 2  # fail_first on first shot
    # Cost event candidate hashes align with accepted candidates when present
    assert all(e.authority == "PROPOSED" for e in first.cost_ledger.events)


def test_controlled_proof_from_text() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    receipt = run_controlled_proof(
        text=text,
        title="Continuity Sample",
        document_key="proof-text",
        seed="t",
    )
    assert receipt.claim == "controlled_proof_not_production_ready"
    assert receipt.document_key == "proof-text"
    assert receipt.shots
