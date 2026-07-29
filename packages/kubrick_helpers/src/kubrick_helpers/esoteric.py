"""Deterministic esoteric concept selection for Kubrick retrieval."""

import re
from typing import Dict, List, Tuple


def _tokens(value) -> set:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return set(re.findall(r"[a-z0-9_]+", str(value).lower().replace("-", "_")))


def _overlap(left, right, neutral: float = 0.45) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return neutral
    return min(1.0, neutral + len(left_tokens & right_tokens) / max(1, len(left_tokens)) * 0.55)


def requested(brief: Dict, index: Dict) -> bool:
    explicit = brief.get("esoteric_encoding")
    if isinstance(explicit, bool):
        return explicit
    if isinstance(explicit, dict):
        return explicit.get("enabled", True)
    searchable = " ".join(
        str(brief.get(key, ""))
        for key in ("request", "dramatic_problem", "desired_state_change", "symbolic_intent")
    ).lower()
    return any(term.lower() in searchable for term in index.get("activation", {}).get("explicit_terms", []))


def _route_bonus(concept_id: str, brief: Dict, index: Dict) -> float:
    problem = _tokens(brief.get("dramatic_problem", "")) | _tokens(brief.get("desired_state_change", ""))
    return max(
        [
            0.16
            for route, concept_ids in index.get("problem_routes", {}).items()
            if concept_id in concept_ids and _tokens(route) & problem
        ]
        or [0.0]
    )


def score(concept_id: str, concept: Dict, brief: Dict, index: Dict) -> Dict:
    dramatic_fit = _overlap(
        [brief.get("dramatic_problem", ""), brief.get("desired_state_change", "")],
        concept.get("dramatic_operations", []) + concept.get("state_changes", []),
    )
    cinematic_fit = _overlap(
        brief.get("preferred_encoding_vectors", []), concept.get("vectors", []), neutral=0.65
    )
    source_quality = {
        "PRIMARY": 0.95,
        "SCHOLARLY": 0.85,
        "PRACTITIONER": 0.75,
        "COMPARATIVE": 0.65,
    }.get(concept.get("source_tier", "COMPARATIVE"), 0.55)
    mutation_potential = 0.9 if concept.get("mutation") else 0.0
    boundary_quality = 0.9 if concept.get("boundary") else 0.0
    ledger_bonus = 0.12 if concept_id in set(brief.get("active_project_grammars", [])) else 0.0
    total = (
        dramatic_fit * 0.35
        + cinematic_fit * 0.15
        + source_quality * 0.15
        + mutation_potential * 0.15
        + boundary_quality * 0.10
        + _route_bonus(concept_id, brief, index)
        + ledger_bonus
    )
    if concept_id in set(brief.get("prohibited_concepts", [])):
        total = 0.0
    return {
        "concept_id": concept_id,
        "tradition": concept.get("tradition"),
        "dramatic_function": concept.get("dramatic_operations", ["transform"])[0],
        "encoding_vectors": concept.get("vectors", []),
        "mutation_rule": concept.get("mutation"),
        "provenance": concept.get("provenance", []),
        "tradition_boundary": concept.get("boundary"),
        "misuse_risks": concept.get("misuse_risks", []),
        "total_score": round(max(0.0, min(1.0, total)), 4),
    }


def rank(brief: Dict, index: Dict) -> Tuple[List[Dict], List[Dict]]:
    prohibited = set(brief.get("prohibited_concepts", []))
    ranked: List[Dict] = []
    rejected: List[Dict] = []
    for concept_id, concept in index.get("concepts", {}).items():
        if concept_id in prohibited:
            rejected.append({"concept_id": concept_id, "reason": "explicitly prohibited"})
            continue
        ranked.append(score(concept_id, concept, brief, index))
    ranked.sort(key=lambda item: (-item["total_score"], item["concept_id"]))
    return ranked, rejected


def select(brief: Dict, index: Dict) -> Dict:
    ranked, rejected = rank(brief, index)
    policy = index.get("selection_policy", {})
    threshold = float(policy.get("minimum_score", 0.55))
    limit = int(policy.get("primary_limit", 1)) + int(policy.get("secondary_limit", 2))
    selected = [item for item in ranked if item["total_score"] >= threshold][:limit]
    evidence = brief.get("observable_evidence", [])
    if not evidence:
        rejected.extend(
            {"concept_id": item["concept_id"], "reason": "observable evidence missing"}
            for item in selected
        )
        selected = []

    selections = [
        {
            "concept_id": item["concept_id"],
            "tradition": item["tradition"],
            "dramatic_function": item["dramatic_function"],
            "encoding_vectors": item["encoding_vectors"],
            "observable_evidence": evidence,
            "mutation_rule": item["mutation_rule"],
            "inversion_condition": None,
            "payoff_condition": None,
            "residue": None,
            "audience_visibility": brief.get(
                "audience_visibility", policy.get("audience_surface_default", "peripheral")
            ),
            "confidence": item["total_score"],
            "provenance": item["provenance"],
            "tradition_boundary": item["tradition_boundary"],
        }
        for item in selected
    ]
    return {
        "status": "SELECTED" if selections else policy.get("fail_closed", "NOT_COMPUTABLE"),
        "schema_version": "1.0.0",
        "governing_grammar": selections[0]["concept_id"] if selections else None,
        "selections": selections,
        "rejected_concepts": rejected,
        "ranked_concepts": ranked[:8] if selections else [],
        "canon_status": policy.get("canon_status_default", "PROPOSED"),
    }
