"""Deterministic generator-evaluator-repair loop over mock candidates."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from continuity_forge_ir import content_hash, stable_id
from continuity_forge_providers import (
    ArtifactCandidate,
    Authority,
    ProviderGateway,
    WorkerTask,
)
from pydantic import BaseModel, Field


class ValidationSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class ValidationFinding(BaseModel):
    code: str
    severity: ValidationSeverity
    message: str


class ValidationReport(BaseModel):
    shot_id: UUID
    candidate_id: UUID
    passed: bool
    findings: list[ValidationFinding] = Field(default_factory=list)


class RepairAction(StrEnum):
    REGENERATE = "regenerate"
    INCLUDE_MISSING_ENTITIES = "include_missing_entities"
    DROP_SOFT_TARGET = "drop_soft_target"


class RepairPlan(BaseModel):
    plan_id: UUID
    actions: list[RepairAction]
    rationale: str


class LoopAttempt(BaseModel):
    attempt: int
    candidate: ArtifactCandidate
    validation: ValidationReport
    repair_plan: RepairPlan | None = None


class LoopResult(BaseModel):
    shot_id: UUID
    status: str
    attempts: list[LoopAttempt]
    accepted_candidate: ArtifactCandidate | None = None
    authority: Authority = Authority.PROPOSED


def validate_candidate(
    shot_contract: dict[str, Any], candidate: ArtifactCandidate
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    required = {str(e) for e in shot_contract.get("required_entity_ids") or []}
    present = {str(e) for e in (candidate.feature_bag.get("entity_ids") or [])}
    missing = sorted(required - present)
    if missing:
        findings.append(
            ValidationFinding(
                code="missing_required_entity",
                severity=ValidationSeverity.HARD,
                message=f"Missing required entities: {', '.join(missing)}",
            )
        )

    prohibited = {
        str(c.get("entity_id"))
        for c in shot_contract.get("constraints") or []
        if c.get("code") == "forbid_prop" and c.get("entity_id")
    }
    seen_prohibited = prohibited.intersection(present)
    # Also fail if feature bag claims prohibited_seen
    for entity_id in candidate.feature_bag.get("prohibited_seen") or []:
        seen_prohibited.add(str(entity_id))
    if seen_prohibited:
        findings.append(
            ValidationFinding(
                code="prohibited_prop_present",
                severity=ValidationSeverity.HARD,
                message=f"Prohibited props present: {', '.join(sorted(seen_prohibited))}",
            )
        )

    if candidate.feature_bag.get("start_state_hash") != shot_contract.get("start_state_hash"):
        findings.append(
            ValidationFinding(
                code="start_state_mismatch",
                severity=ValidationSeverity.HARD,
                message="Candidate start_state_hash does not match shot contract.",
            )
        )

    hard = [f for f in findings if f.severity == ValidationSeverity.HARD]
    return ValidationReport(
        shot_id=candidate.shot_id,
        candidate_id=candidate.candidate_id,
        passed=not hard,
        findings=findings,
    )


def plan_repair(report: ValidationReport) -> RepairPlan:
    actions: list[RepairAction] = []
    codes = {f.code for f in report.findings}
    if "missing_required_entity" in codes:
        actions.append(RepairAction.INCLUDE_MISSING_ENTITIES)
        actions.append(RepairAction.REGENERATE)
    if "prohibited_prop_present" in codes:
        actions.append(RepairAction.REGENERATE)
    if not actions:
        actions.append(RepairAction.REGENERATE)
    rationale = "; ".join(f.message for f in report.findings) or "unspecified failure"
    return RepairPlan(
        plan_id=stable_id("repair", report.shot_id, report.candidate_id, rationale),
        actions=actions,
        rationale=rationale,
    )


def run_repair_loop(
    shot_contract: dict[str, Any],
    *,
    gateway: ProviderGateway | None = None,
    seed: str = "0",
    max_attempts: int = 3,
    fail_first: bool = False,
) -> LoopResult:
    """Run generate → validate → repair with bounded attempts.

    When fail_first is True, attempt 1 omits an entity to force one repair cycle
    (deterministic controlled proof of the loop).
    """
    active = gateway or ProviderGateway()
    attempts: list[LoopAttempt] = []
    shot_id = UUID(str(shot_contract["shot_id"]))

    for attempt in range(1, max_attempts + 1):
        force_missing = fail_first and attempt == 1
        candidate = active.generate_for_shot(
            shot_contract,
            seed=f"{seed}:{attempt}",
            task=WorkerTask.IMAGE,
            force_missing_entities=force_missing,
        )
        report = validate_candidate(shot_contract, candidate)
        repair = None if report.passed else plan_repair(report)
        attempts.append(
            LoopAttempt(
                attempt=attempt,
                candidate=candidate,
                validation=report,
                repair_plan=repair,
            )
        )
        if report.passed:
            accepted = candidate.model_copy(update={"authority": Authority.PROPOSED})
            return LoopResult(
                shot_id=shot_id,
                status="accepted_proposed",
                attempts=attempts,
                accepted_candidate=accepted,
                authority=Authority.PROPOSED,
            )

    return LoopResult(
        shot_id=shot_id,
        status="rejected",
        attempts=attempts,
        accepted_candidate=None,
        authority=Authority.REJECTED,
    )


def loop_receipt_hash(result: LoopResult) -> str:
    return content_hash(result.model_dump_json())
