"""Controlled end-to-end proof runner (mock media only)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from continuity_forge_ir import content_hash
from continuity_forge_operator import MutationEnvelope, ProjectStore
from continuity_forge_providers import ProviderGateway
from pydantic import BaseModel, Field

from continuity_forge_repair.loop import run_repair_loop


class ShotProof(BaseModel):
    shot_id: str
    scene_id: str
    label: str
    status: str
    attempts: int
    accepted_candidate_hash: str | None = None
    repair_actions: list[str] = Field(default_factory=list)


class ProofReceipt(BaseModel):
    schema_version: str = "m7.proof.v1"
    claim: str = "controlled_proof_not_production_ready"
    document_key: str
    source_hash: str
    production_ir_hash: str | None
    ledger_hash: str | None
    shot_contracts_hash: str | None
    elapsed_seconds: float
    budget_seconds: float = 60.0
    within_budget: bool
    shots: list[ShotProof]
    receipt_hash: str


def run_controlled_proof(
    script_path: Path | None = None,
    *,
    text: str | None = None,
    title: str | None = None,
    format: Literal["fountain", "fdx"] = "fountain",
    store: ProjectStore | None = None,
    gateway: ProviderGateway | None = None,
    document_key: str | None = None,
    actor_id: str = "proof-operator",
    seed: str = "proof",
    budget_seconds: float = 60.0,
) -> ProofReceipt:
    """Run ingest → kernel pipeline → mock generate/validate/repair for each master shot.

    Provide either ``script_path`` or ``text``. Receipt claims
    ``controlled_proof_not_production_ready`` (mock media only).
    """
    if text is None and script_path is None:
        raise ValueError("script_path or text is required")
    if text is None:
        assert script_path is not None
        source = script_path.read_text(encoding="utf-8")
        key = document_key or script_path.stem
        script_title = title or script_path.stem
        script_format: Literal["fountain", "fdx"] = (
            "fdx" if script_path.suffix.casefold() == ".fdx" else "fountain"
        )
    else:
        source = text
        key = document_key or "document"
        script_title = title or key
        script_format = format

    active = store or ProjectStore()
    started = time.perf_counter()

    active.acquire_lease(key, actor_id, ttl_seconds=600)
    try:
        envelope = MutationEnvelope(
            actor_id=actor_id,
            authorization_scope="kernel:pipeline",
            idempotency_key=f"proof-{key}-{content_hash(source)[:12]}",
            rationale="M7 controlled proof ingest",
        )
        project, run = active.ingest_script(
            document_key=key,
            title=script_title,
            text=source,
            revision="0.1.0",
            format=script_format,
            envelope=envelope,
        )
    finally:
        active.release_lease(key, actor_id)

    contracts = (project.shot_contracts or {}).get("contracts") or []
    shot_proofs: list[ShotProof] = []
    for index, contract in enumerate(contracts):
        # Force one repair cycle on the first shot only for proof of loop behavior.
        result = run_repair_loop(
            contract,
            gateway=gateway,
            seed=f"{seed}:{index}",
            fail_first=(index == 0),
        )
        repair_actions: list[str] = []
        for attempt in result.attempts:
            if attempt.repair_plan:
                repair_actions.extend(a.value for a in attempt.repair_plan.actions)
        shot_proofs.append(
            ShotProof(
                shot_id=str(contract["shot_id"]),
                scene_id=str(contract["scene_id"]),
                label=str(contract.get("label") or ""),
                status=result.status,
                attempts=len(result.attempts),
                accepted_candidate_hash=(
                    result.accepted_candidate.content_hash if result.accepted_candidate else None
                ),
                repair_actions=repair_actions,
            )
        )

    elapsed = time.perf_counter() - started
    artifacts = run.artifacts
    receipt = ProofReceipt(
        document_key=key,
        source_hash=project.source_hash,
        production_ir_hash=artifacts.production_ir_hash if artifacts else None,
        ledger_hash=artifacts.ledger_hash if artifacts else None,
        shot_contracts_hash=artifacts.shot_contracts_hash if artifacts else None,
        elapsed_seconds=elapsed,
        budget_seconds=budget_seconds,
        within_budget=elapsed <= budget_seconds,
        shots=shot_proofs,
        receipt_hash="",
    )
    receipt = receipt.model_copy(
        update={"receipt_hash": content_hash(receipt.model_dump_json(exclude={"receipt_hash"}))}
    )
    return receipt


def proof_to_dict(receipt: ProofReceipt) -> dict[str, Any]:
    return receipt.model_dump(mode="json")
