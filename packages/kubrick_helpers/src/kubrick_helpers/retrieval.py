#!/usr/bin/env python3
"""Importable and CLI Kubrick symbolic retrieval with optional esoteric selection."""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    print("pyyaml required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

from .esoteric import requested as esoteric_requested
from .esoteric import select as select_esoteric

DEFAULT_INDEX_PATH = None
DEFAULT_ESOTERIC_INDEX_PATH = None
DEFAULT_PATTERNS_DIR = None

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


def load_index(index_path: str = None) -> Dict:
    path = index_path or DEFAULT_INDEX_PATH
    if path is None:
        raise ValueError("index_path must be provided or set")
    return load_yaml(path)


def load_esoteric_index(index_path: str = None) -> Dict:
    path = index_path or DEFAULT_ESOTERIC_INDEX_PATH
    if path is None:
        raise ValueError("esoteric_index_path must be provided when esoteric retrieval is active")
    return load_yaml(path)


def load_all_patterns(patterns_dir: str = None) -> Dict[str, Dict]:
    directory = patterns_dir or DEFAULT_PATTERNS_DIR
    if directory is None:
        raise ValueError("patterns_dir must be provided")
    patterns: Dict[str, Dict] = {}
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".json"):
                with open(os.path.join(root, filename), "r", encoding="utf-8") as handle:
                    pattern = json.load(handle)
                patterns[pattern["pattern_id"]] = pattern
    return patterns


def compute_score(pattern: Dict, brief: Dict, weights: Dict = None) -> Dict:
    weights = weights or DEFAULT_WEIGHTS
    components: Dict[str, float] = {}
    problem = brief.get("dramatic_problem", "").lower().split()
    operations = " ".join(pattern.get("dramatic_operations", [])).lower()
    components["dramatic_fit"] = 0.95 if any(term in operations for term in problem) else 0.7

    genres = [str(item).lower() for item in pattern.get("applicable_genres", [])]
    cinematic = 0.9 if brief.get("genre", "").lower() in genres else 0.6
    if brief.get("format") in pattern.get("applicable_formats", []):
        cinematic += 0.05
    components["cinematic_fit"] = min(cinematic, 1.0)

    context = brief.get("cultural_context", "").lower()
    scopes = " ".join(pattern.get("cultural_scope", [])).lower()
    components["cultural_fit"] = 0.85 if context and any(term in scopes for term in context.split()) else 0.5
    components["source_quality"] = {
        "PRIMARY": 0.95,
        "SCHOLARLY": 0.85,
        "PRACTITIONER": 0.75,
        "COMPARATIVE": 0.65,
    }.get(pattern.get("source_tier", "POPULAR"), 0.5)
    components["mutation_potential"] = (
        0.9 if pattern.get("mutation_requirements", {}).get("required", False) else 0.6
    )
    active = brief.get("active_project_motifs", [])
    components["continuity_compatibility"] = (
        0.6 if any(motif in str(pattern) for motif in active) else 0.8
    )
    components["character_fit"] = 0.7
    components["cliché_risk"] = 0.3

    total = sum(components.get(key, 0.5) * weight for key, weight in weights.items())
    total -= components["cliché_risk"] * 0.20
    return {
        "total_score": round(max(0.0, min(1.0, total)), 4),
        "score_components": {key: round(value, 4) for key, value in components.items()},
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


def rank_patterns(brief: Dict, patterns_db: Dict, weights: Dict = None) -> Tuple[List[Dict], List[Dict]]:
    candidates = [
        pattern
        for pattern in patterns_db.values()
        if compute_score(pattern, brief, weights)["total_score"] >= 0.3
    ]
    filtered, rejected = apply_exclusions(candidates, brief)
    ranked = []
    for pattern in filtered:
        score_data = compute_score(pattern, brief, weights)
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


def build_receipt(
    brief: Dict,
    ranked: List[Dict],
    rejected_patterns: List[Dict],
    esoteric_selection: Dict = None,
) -> Dict:
    request_hash = hashlib.sha256(json.dumps(brief, sort_keys=True).encode()).hexdigest()[:16]
    primary = ranked[0] if ranked else None
    supporting = ranked[1 : 1 + MAX_SUPPORTING]
    pattern_status = "SELECTED" if primary and primary["total_score"] >= THRESHOLD else "NOT_COMPUTABLE"
    status = pattern_status
    if esoteric_selection and esoteric_selection.get("status") == "NOT_COMPUTABLE":
        status = "NOT_COMPUTABLE"
    return {
        "retrieval_receipt": {
            "request_hash": request_hash,
            "corpus_version": "0.8.1",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "selected_primary_grammar": primary["pattern_id"] if primary else None,
            "selected_supporting_grammars": [item["pattern_id"] for item in supporting],
            "ranked_patterns": ranked[:5] if pattern_status == "SELECTED" else [],
            "rejected_patterns": rejected_patterns,
            "confidence": primary["total_score"] if primary else 0.0,
            "pattern_status": pattern_status,
            "esoteric_encoding": esoteric_selection,
            "status": status,
            "brief": brief,
        }
    }


def log_receipt(receipt: Dict, log_dir: str = None) -> str:
    log_dir = log_dir or os.environ.get("KUBRICK_USAGE_RECEIPTS") or os.path.join(
        os.getcwd(), "kubrick_usage_receipts"
    )
    os.makedirs(log_dir, exist_ok=True)
    request_hash = receipt.get("retrieval_receipt", {}).get("request_hash", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = os.path.join(log_dir, f"receipt-{request_hash}-{timestamp}.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    return path


def run_retrieval(
    brief: Dict,
    index_path: str = None,
    patterns_dir: str = None,
    esoteric_index_path: str = None,
) -> Dict:
    patterns_db = load_all_patterns(patterns_dir)
    ranked, rejected = rank_patterns(brief, patterns_db)

    esoteric_selection = None
    candidate_esoteric_index = esoteric_index_path or DEFAULT_ESOTERIC_INDEX_PATH
    if candidate_esoteric_index:
        esoteric_index = load_esoteric_index(candidate_esoteric_index)
        if esoteric_requested(brief, esoteric_index):
            esoteric_selection = select_esoteric(brief, esoteric_index)
    elif brief.get("esoteric_encoding"):
        esoteric_selection = {
            "status": "NOT_COMPUTABLE",
            "schema_version": "1.0.0",
            "governing_grammar": None,
            "selections": [],
            "rejected_concepts": [
                {"concept_id": "<all>", "reason": "esoteric index path unavailable"}
            ],
            "ranked_concepts": [],
            "canon_status": "PROPOSED",
        }

    receipt = build_receipt(brief, ranked, rejected, esoteric_selection)
    try:
        receipt["retrieval_receipt"]["logged_to"] = log_receipt(receipt)
    except OSError:
        pass
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=str, help="Path to YAML/JSON brief")
    parser.add_argument("--index", type=str, help="Path to corpus-index.yaml")
    parser.add_argument("--patterns", type=str, help="Path to patterns directory")
    parser.add_argument("--esoteric-index", type=str, help="Path to esoteric-concept-index.yaml")
    args = parser.parse_args()

    if args.brief:
        with open(args.brief, "r", encoding="utf-8") as handle:
            brief = json.load(handle) if args.brief.endswith(".json") else yaml.safe_load(handle)
    else:
        brief = yaml.safe_load(sys.stdin) or {}

    receipt = run_retrieval(
        brief or {},
        index_path=args.index,
        patterns_dir=args.patterns,
        esoteric_index_path=args.esoteric_index,
    )
    print(yaml.safe_dump(receipt, sort_keys=False))
    if receipt["retrieval_receipt"]["status"] == "NOT_COMPUTABLE":
        sys.exit(1)


if __name__ == "__main__":
    main()
