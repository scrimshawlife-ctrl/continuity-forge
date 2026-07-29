#!/usr/bin/env python3
"""
Kubrick Retrieval Helper — deterministic symbolic pattern and esoteric concept retrieval.

The normal pattern retriever remains the default. The esoteric concept layer activates
only when the brief explicitly requests it or contains a configured activation term.
Both paths fail closed below threshold and emit auditable receipts.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    print("pyyaml required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
INDEX_PATH = os.path.join(SKILL_ROOT, "references", "corpus-index.yaml")
ESOTERIC_INDEX_PATH = os.path.join(SKILL_ROOT, "references", "esoteric-concept-index.yaml")
PATTERNS_DIR = os.path.join(SKILL_ROOT, "references", "patterns")

DEFAULT_WEIGHTS = {
    "dramatic_fit": 0.25,
    "character_fit": 0.15,
    "cultural_fit": 0.15,
    "cinematic_fit": 0.15,
    "source_quality": 0.10,
    "mutation_potential": 0.10,
    "continuity_compatibility": 0.10,
}

THRESHOLD = 0.55
MAX_SUPPORTING = 2


def load_yaml(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_index() -> Dict:
    return load_yaml(INDEX_PATH)


def load_esoteric_index() -> Dict:
    return load_yaml(ESOTERIC_INDEX_PATH)


def load_all_patterns() -> Dict[str, Dict]:
    patterns: Dict[str, Dict] = {}
    for root, _, files in os.walk(PATTERNS_DIR):
        for filename in files:
            if filename.endswith(".json"):
                with open(os.path.join(root, filename), "r", encoding="utf-8") as handle:
                    pattern = json.load(handle)
                patterns[pattern["pattern_id"]] = pattern
    return patterns


def tokenize(value) -> set:
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return set(re.findall(r"[a-z0-9_]+", str(value).lower().replace("-", "_")))


def overlap_score(left, right, neutral: float = 0.45) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return neutral
    overlap = len(left_tokens & right_tokens)
    return min(1.0, neutral + (overlap / max(1, len(left_tokens))) * 0.55)


def compute_score(pattern: Dict, brief: Dict, weights: Dict = None) -> Dict:
    weights = weights or DEFAULT_WEIGHTS
    score_components: Dict[str, float] = {}

    score_components["dramatic_fit"] = overlap_score(
        brief.get("dramatic_problem", ""), pattern.get("dramatic_operations", [])
    )

    genres = [str(item).lower() for item in pattern.get("applicable_genres", [])]
    cinematic = 0.6
    if brief.get("genre", "").lower() in genres:
        cinematic = 0.9
    if brief.get("format") in pattern.get("applicable_formats", []):
        cinematic += 0.05
    score_components["cinematic_fit"] = min(cinematic, 1.0)

    score_components["cultural_fit"] = overlap_score(
        brief.get("cultural_context", ""), pattern.get("cultural_scope", []), neutral=0.5
    )

    tier = pattern.get("source_tier", "POPULAR")
    score_components["source_quality"] = {
        "PRIMARY": 0.95,
        "SCHOLARLY": 0.85,
        "PRACTITIONER": 0.75,
        "COMPARATIVE": 0.65,
    }.get(tier, 0.5)

    mutation_required = pattern.get("mutation_requirements", {}).get("required", False)
    score_components["mutation_potential"] = 0.9 if mutation_required else 0.6

    active = brief.get("active_project_motifs", [])
    score_components["continuity_compatibility"] = (
        0.6 if any(motif in str(pattern) for motif in active) else 0.8
    )
    score_components["character_fit"] = 0.7
    score_components["cliché_risk"] = 0.3

    total = sum(score_components.get(key, 0.5) * weight for key, weight in weights.items())
    total -= score_components["cliché_risk"] * 0.20
    return {
        "total_score": round(max(0.0, min(1.0, total)), 4),
        "score_components": {key: round(value, 4) for key, value in score_components.items()},
    }


def apply_exclusions(patterns: List[Dict], brief: Dict) -> Tuple[List[Dict], List[Dict]]:
    prohibited = [item.lower() for item in brief.get("prohibited_patterns", [])]
    accepted: List[Dict] = []
    rejected: List[Dict] = []
    for pattern in patterns:
        pattern_id = pattern["pattern_id"].lower()
        title = pattern.get("title", "").lower()
        match = next((item for item in prohibited if item in pattern_id or item in title), None)
        if match:
            rejected.append({"pattern_id": pattern["pattern_id"], "reason": f"prohibited:{match}"})
        else:
            accepted.append(pattern)
    return accepted, rejected


def rank_patterns(brief: Dict, patterns_db: Dict) -> Tuple[List[Dict], List[Dict]]:
    candidates = []
    for pattern in patterns_db.values():
        score_data = compute_score(pattern, brief, DEFAULT_WEIGHTS)
        if score_data["total_score"] >= 0.3:
            candidates.append(pattern)

    filtered, rejected = apply_exclusions(candidates, brief)
    ranked = []
    for pattern in filtered:
        score_data = compute_score(pattern, brief, DEFAULT_WEIGHTS)
        ranked.append(
            {
                "pattern_id": pattern["pattern_id"],
                "total_score": score_data["total_score"],
                "score_components": score_data["score_components"],
                "provenance_refs": pattern.get("source_refs", []),
                "mutation_requirements": pattern.get("mutation_requirements", {}),
                "production_cost": pattern.get("production_cost", {}),
                "selection_reason": "dramatic and cinematic fit after exclusions",
            }
        )
    ranked.sort(key=lambda item: (-item["total_score"], item["pattern_id"]))
    return ranked, rejected


def esoteric_requested(brief: Dict, index: Dict) -> bool:
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


def route_bonus(concept_id: str, brief: Dict, index: Dict) -> float:
    problem_tokens = tokenize(brief.get("dramatic_problem", "")) | tokenize(
        brief.get("desired_state_change", "")
    )
    bonus = 0.0
    for route_name, concept_ids in index.get("problem_routes", {}).items():
        if concept_id in concept_ids and tokenize(route_name) & problem_tokens:
            bonus = max(bonus, 0.16)
    return bonus


def score_esoteric_concept(concept_id: str, concept: Dict, brief: Dict, index: Dict) -> Dict:
    dramatic_fit = overlap_score(
        [brief.get("dramatic_problem", ""), brief.get("desired_state_change", "")],
        concept.get("dramatic_operations", []) + concept.get("state_changes", []),
    )
    cinematic_fit = overlap_score(
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

    active_grammars = set(brief.get("active_project_grammars", []))
    ledger_bonus = 0.12 if concept_id in active_grammars else 0.0
    score = (
        dramatic_fit * 0.35
        + cinematic_fit * 0.15
        + source_quality * 0.15
        + mutation_potential * 0.15
        + boundary_quality * 0.10
        + route_bonus(concept_id, brief, index)
        + ledger_bonus
    )

    prohibited = set(brief.get("prohibited_concepts", []))
    if concept_id in prohibited:
        score = 0.0

    return {
        "concept_id": concept_id,
        "tradition": concept.get("tradition"),
        "dramatic_function": concept.get("dramatic_operations", ["transform"])[0],
        "encoding_vectors": concept.get("vectors", []),
        "mutation_rule": concept.get("mutation"),
        "provenance": concept.get("provenance", []),
        "tradition_boundary": concept.get("boundary"),
        "misuse_risks": concept.get("misuse_risks", []),
        "total_score": round(max(0.0, min(1.0, score)), 4),
        "score_components": {
            "dramatic_fit": round(dramatic_fit, 4),
            "cinematic_fit": round(cinematic_fit, 4),
            "source_quality": round(source_quality, 4),
            "mutation_potential": round(mutation_potential, 4),
            "boundary_quality": round(boundary_quality, 4),
            "route_bonus": round(route_bonus(concept_id, brief, index), 4),
            "ledger_bonus": round(ledger_bonus, 4),
        },
    }


def rank_esoteric_concepts(brief: Dict, index: Dict) -> Tuple[List[Dict], List[Dict]]:
    ranked = []
    rejected = []
    prohibited = set(brief.get("prohibited_concepts", []))
    for concept_id, concept in index.get("concepts", {}).items():
        item = score_esoteric_concept(concept_id, concept, brief, index)
        if concept_id in prohibited:
            rejected.append({"concept_id": concept_id, "reason": "explicitly prohibited"})
        else:
            ranked.append(item)
    ranked.sort(key=lambda item: (-item["total_score"], item["concept_id"]))
    return ranked, rejected


def build_esoteric_selection(brief: Dict, ranked: List[Dict], rejected: List[Dict], index: Dict) -> Dict:
    policy = index.get("selection_policy", {})
    threshold = float(policy.get("minimum_score", THRESHOLD))
    qualifying = [item for item in ranked if item["total_score"] >= threshold]
    primary_limit = int(policy.get("primary_limit", 1))
    secondary_limit = int(policy.get("secondary_limit", 2))
    selection_limit = primary_limit + secondary_limit
    selected = qualifying[:selection_limit]

    status = "SELECTED" if selected else policy.get("fail_closed", "NOT_COMPUTABLE")
    observable_evidence = brief.get("observable_evidence", [])
    if not observable_evidence:
        status = "NOT_COMPUTABLE"
        rejected = rejected + [
            {"concept_id": item["concept_id"], "reason": "observable evidence missing"}
            for item in selected
        ]
        selected = []

    output_selections = []
    for item in selected:
        output_selections.append(
            {
                "concept_id": item["concept_id"],
                "tradition": item["tradition"],
                "dramatic_function": item["dramatic_function"],
                "encoding_vectors": item["encoding_vectors"],
                "observable_evidence": observable_evidence,
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
        )

    return {
        "status": status,
        "schema_version": "1.0.0",
        "governing_grammar": selected[0]["concept_id"] if selected else None,
        "selections": output_selections,
        "rejected_concepts": rejected,
        "ranked_concepts": ranked[:8] if status == "SELECTED" else [],
        "canon_status": policy.get("canon_status_default", "PROPOSED"),
    }


def build_receipt(
    brief: Dict,
    ranked_patterns: List[Dict],
    rejected_patterns: List[Dict],
    esoteric_selection: Dict = None,
) -> Dict:
    request_str = json.dumps(brief, sort_keys=True)
    request_hash = hashlib.sha256(request_str.encode()).hexdigest()[:16]

    primary = ranked_patterns[0] if ranked_patterns else None
    supporting = ranked_patterns[1 : 1 + MAX_SUPPORTING]
    pattern_status = "SELECTED" if primary and primary["total_score"] >= THRESHOLD else "NOT_COMPUTABLE"
    overall_status = pattern_status
    if esoteric_selection and esoteric_selection["status"] == "NOT_COMPUTABLE":
        overall_status = "NOT_COMPUTABLE"

    return {
        "retrieval_receipt": {
            "request_hash": request_hash,
            "corpus_version": "0.8.1",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "selected_primary_grammar": primary["pattern_id"] if primary else None,
            "selected_supporting_grammars": [item["pattern_id"] for item in supporting],
            "ranked_patterns": ranked_patterns[:5] if pattern_status == "SELECTED" else [],
            "rejected_patterns": rejected_patterns,
            "confidence": primary["total_score"] if primary else 0.0,
            "pattern_status": pattern_status,
            "esoteric_encoding": esoteric_selection,
            "status": overall_status,
            "brief": brief,
        }
    }


def log_receipt(receipt: Dict, log_dir: str = None) -> str:
    log_dir = log_dir or os.path.join(SKILL_ROOT, "references", "usage", "receipts")
    os.makedirs(log_dir, exist_ok=True)
    request_hash = receipt.get("retrieval_receipt", {}).get("request_hash", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(log_dir, f"receipt-{request_hash}-{timestamp}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    return path


def run_retrieval(brief: Dict) -> Dict:
    patterns_db = load_all_patterns()
    ranked_patterns, rejected_patterns = rank_patterns(brief, patterns_db)

    esoteric_index = load_esoteric_index()
    esoteric_selection = None
    if esoteric_requested(brief, esoteric_index):
        ranked_concepts, rejected_concepts = rank_esoteric_concepts(brief, esoteric_index)
        esoteric_selection = build_esoteric_selection(
            brief, ranked_concepts, rejected_concepts, esoteric_index
        )

    receipt = build_receipt(
        brief, ranked_patterns, rejected_patterns, esoteric_selection=esoteric_selection
    )
    receipt["retrieval_receipt"]["logged_to"] = log_receipt(receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=str, help="Path to YAML/JSON brief")
    args = parser.parse_args()

    if args.brief:
        with open(args.brief, "r", encoding="utf-8") as handle:
            brief = json.load(handle) if args.brief.endswith(".json") else yaml.safe_load(handle)
    else:
        brief = yaml.safe_load(sys.stdin) or {}

    receipt = run_retrieval(brief or {})
    print(yaml.dump(receipt, sort_keys=False, default_flow_style=False))
    if receipt["retrieval_receipt"]["status"] == "NOT_COMPUTABLE":
        sys.exit(1)


if __name__ == "__main__":
    main()
