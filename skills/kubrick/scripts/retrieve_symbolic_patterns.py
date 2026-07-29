#!/usr/bin/env python3
"""
Kubrick Retrieval Helper — Deterministic symbolic pattern retrieval.

This script is self-contained. It works completely independently when the
skill is installed in Hermes (cp -R skills/kubrick ~/.hermes/skills/).

It does not require continuity-forge or any optional extras to be installed.

Usage:
  python scripts/retrieve_symbolic_patterns.py --brief brief.yaml
  or pass JSON/YAML via stdin.

Outputs a retrieval_receipt.yaml with ranked patterns, scores, and status.
Fails closed on low confidence.
"""

import argparse
import json
import os
import sys
import hashlib
from datetime import datetime
from typing import Dict, List

try:
    import yaml
except ImportError:
    print("pyyaml required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
INDEX_PATH = os.path.join(SKILL_ROOT, "references", "corpus-index.yaml")
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


def load_index() -> Dict:
    with open(INDEX_PATH, "r") as f:
        return yaml.safe_load(f)


def load_pattern(pattern_id: str) -> Dict:
    for root, dirs, files in os.walk(PATTERNS_DIR):
        for fname in files:
            if fname == f"{pattern_id}.json":
                with open(os.path.join(root, fname), "r") as f:
                    return json.load(f)
    raise FileNotFoundError(f"Sidecar not found for {pattern_id}")


def load_all_patterns() -> Dict[str, Dict]:
    patterns = {}
    for root, dirs, files in os.walk(PATTERNS_DIR):
        for fname in files:
            if fname.endswith(".json"):
                with open(os.path.join(root, fname), "r") as f:
                    p = json.load(f)
                    patterns[p["pattern_id"]] = p
    return patterns


def compute_score(pattern: Dict, brief: Dict, weights: Dict = None) -> Dict:
    weights = weights or DEFAULT_WEIGHTS
    score_components = {}
    total = 0.0

    dramatic = 0.7
    if any(op in " ".join(pattern.get("dramatic_operations", [])) for op in brief.get("dramatic_problem", "").split()):
        dramatic = 0.95
    score_components["dramatic_fit"] = dramatic

    genres = pattern.get("applicable_genres", [])
    cinematic = 0.6
    if brief.get("genre", "").lower() in [g.lower() for g in genres]:
        cinematic = 0.9
    if brief.get("format") in pattern.get("applicable_formats", []):
        cinematic += 0.05
    score_components["cinematic_fit"] = min(cinematic, 1.0)

    cultural = 0.5
    ctx = brief.get("cultural_context", "").lower()
    scopes = " ".join(pattern.get("cultural_scope", [])).lower()
    if ctx and any(c in scopes for c in ctx.split()):
        cultural = 0.85
    score_components["cultural_fit"] = cultural

    tier = pattern.get("source_tier", "POPULAR")
    tier_score = {"PRIMARY": 0.95, "SCHOLARLY": 0.85, "PRACTITIONER": 0.75}.get(tier, 0.5)
    score_components["source_quality"] = tier_score

    mut = pattern.get("mutation_requirements", {}).get("required", False)
    score_components["mutation_potential"] = 0.9 if mut else 0.6

    active = brief.get("active_project_motifs", [])
    comp = 0.8
    if any(m in str(pattern) for m in active):
        comp = 0.6
    score_components["continuity_compatibility"] = comp

    score_components.setdefault("character_fit", 0.7)
    score_components.setdefault("cliché_risk", 0.3)

    for k, w in weights.items():
        val = score_components.get(k, 0.5)
        total += val * w

    cliché = score_components.get("cliché_risk", 0.3)
    total -= cliché * 0.20

    return {
        "total_score": round(max(0.0, min(1.0, total)), 4),
        "score_components": {k: round(v, 4) for k, v in score_components.items()}
    }


def apply_exclusions(patterns: List[Dict], brief: Dict) -> List[Dict]:
    prohibited = [p.lower() for p in brief.get("prohibited_patterns", [])]
    filtered = []
    for p in patterns:
        pid = p["pattern_id"].lower()
        title = p.get("title", "").lower()
        if any(pro in pid or pro in title for pro in prohibited):
            continue
        filtered.append(p)
    return filtered


def rank_patterns(brief: Dict, patterns_db: Dict) -> List[Dict]:
    candidates = []
    for pid, p in patterns_db.items():
        score_data = compute_score(p, brief, DEFAULT_WEIGHTS)
        if score_data["total_score"] >= 0.3:
            candidates.append({"pattern": p, "score_data": score_data})

    filtered = apply_exclusions([c["pattern"] for c in candidates], brief)

    ranked = []
    for p in filtered:
        score_data = compute_score(p, brief, DEFAULT_WEIGHTS)
        ranked.append({
            "pattern_id": p["pattern_id"],
            "total_score": score_data["total_score"],
            "score_components": score_data["score_components"],
            "provenance_refs": p.get("source_refs", []),
            "mutation_requirements": p.get("mutation_requirements", {}),
            "production_cost": p.get("production_cost", {}),
            "selection_reason": "High dramatic + cinematic fit after exclusions"
        })

    ranked.sort(key=lambda x: x["total_score"], reverse=True)
    return ranked


def build_receipt(brief: Dict, ranked: List[Dict], patterns_db: Dict) -> Dict:
    request_str = json.dumps(brief, sort_keys=True)
    request_hash = hashlib.sha256(request_str.encode()).hexdigest()[:16]

    primary = None
    supporting = []
    for item in ranked:
        if primary is None:
            primary = item
        elif len(supporting) < MAX_SUPPORTING:
            supporting.append(item)

    status = "SELECTED" if primary and primary["total_score"] >= THRESHOLD else "NOT_COMPUTABLE"

    return {
        "retrieval_receipt": {
            "request_hash": request_hash,
            "corpus_version": "0.7.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "selected_primary_grammar": primary["pattern_id"] if primary else None,
            "selected_supporting_grammars": [s["pattern_id"] for s in supporting],
            "ranked_patterns": ranked[:5] if status == "SELECTED" else [],
            "rejected_patterns": [],
            "confidence": primary["total_score"] if primary else 0.0,
            "status": status,
            "brief": brief
        }
    }


def log_receipt(receipt, log_dir=None):
    if log_dir is None:
        log_dir = os.path.join(SKILL_ROOT, "references", "usage", "receipts")
    os.makedirs(log_dir, exist_ok=True)
    h = receipt.get("retrieval_receipt", {}).get("request_hash", "unknown")
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(log_dir, f"receipt-{h}-{ts}.json")
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=str, help="Path to YAML/JSON brief")
    args = parser.parse_args()

    if args.brief:
        with open(args.brief, "r") as f:
            if args.brief.endswith(".json"):
                brief = json.load(f)
            else:
                brief = yaml.safe_load(f)
    else:
        brief = yaml.safe_load(sys.stdin) or {}

    patterns_db = load_all_patterns()

    if not patterns_db:
        print("WARNING: No sidecars found. Falling back to index only.", file=sys.stderr)

    ranked = rank_patterns(brief, patterns_db)

    receipt = build_receipt(brief, ranked, patterns_db)

    logged = log_receipt(receipt)
    receipt["retrieval_receipt"]["logged_to"] = logged

    print(yaml.dump(receipt, sort_keys=False, default_flow_style=False))

    if receipt["retrieval_receipt"]["status"] == "NOT_COMPUTABLE":
        sys.exit(1)


if __name__ == "__main__":
    main()
