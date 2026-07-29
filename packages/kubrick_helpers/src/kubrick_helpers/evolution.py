#!/usr/bin/env python3
"""
Kubrick Self-Evolution Engine (importable + CLI)

Usage (CLI):
  kubrick-evolve --receipts-dir ... --outcomes-dir ...

Usage (import):
  from kubrick_helpers.evolution import run_evolution
  receipt = run_evolution(receipts_dir=..., outcomes_dir=...)

Emits evolution receipt and mutates sidecars in place when paths provided.
"""

import argparse
import json
import os
import glob
from datetime import datetime
from collections import defaultdict
from typing import Dict

try:
    import yaml
except ImportError:
    yaml = None

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_all_sidecars(patterns_dir: str):
    sidecars = {}
    for root, _, files in os.walk(patterns_dir):
        for fname in files:
            if fname.endswith(".json"):
                path = os.path.join(root, fname)
                data = load_json(path)
                sidecars[data.get("pattern_id", fname)] = {"path": path, "data": data}
    return sidecars

def aggregate_usage(receipts_dir, outcomes_dir):
    usage = defaultdict(lambda: {"uses": 0, "total_score": 0.0, "success_signals": 0, "failure_signals": 0, "projects": []})

    for path in glob.glob(os.path.join(receipts_dir, "*.json")) + glob.glob(os.path.join(receipts_dir, "*.yaml")):
        try:
            if path.endswith(".json"):
                receipt = load_json(path)
            else:
                if yaml is None:
                    continue
                receipt = yaml.safe_load(open(path))
            rec = receipt.get("retrieval_receipt", receipt)
            ranked = rec.get("ranked_patterns", [])
            for item in ranked[:3]:
                pid = item.get("pattern_id")
                if pid:
                    usage[pid]["uses"] += 1
                    usage[pid]["total_score"] += item.get("total_score", 0.5)
                    usage[pid]["projects"].append(rec.get("request_hash", "unknown"))
        except Exception as e:
            print(f"Warning: could not parse {path}: {e}")

    for path in glob.glob(os.path.join(outcomes_dir, "*.json")):
        try:
            outcome = load_json(path)
            pid = outcome.get("pattern_id")
            if pid:
                signal = outcome.get("outcome", "neutral")
                if signal == "success":
                    usage[pid]["success_signals"] += 1
                elif signal in ("failure", "debt", "collision", "revision_broken"):
                    usage[pid]["failure_signals"] += 1
                usage[pid]["projects"].append(outcome.get("project", "unknown"))
        except Exception as e:
            print(f"Warning: could not parse outcome {path}: {e}")

    return usage

def evolve_sidecar(sidecar_info, usage_stats):
    data = sidecar_info["data"]
    pid = data["pattern_id"]
    stats = usage_stats.get(pid, {})
    uses = stats.get("uses", 0)
    if uses == 0:
        return None

    avg_score = stats["total_score"] / uses if uses > 0 else 0.5
    success = stats.get("success_signals", 0)
    failure = stats.get("failure_signals", 0)
    total_signals = success + failure or 1
    success_rate = success / total_signals

    current_conf = data.get("confidence", 0.7)
    delta = 0.0

    if uses >= 3:
        delta += (avg_score - 0.6) * 0.15
        delta += (success_rate - 0.5) * 0.25

    if failure > success and uses >= 2:
        delta -= 0.1

    new_conf = max(0.3, min(0.98, round(current_conf + delta, 4)))

    if "usage_history" not in data:
        data["usage_history"] = []
    data["usage_history"].append({
        "date": datetime.utcnow().isoformat() + "Z",
        "uses_in_window": uses,
        "avg_retrieval_score": round(avg_score, 4),
        "success_rate": round(success_rate, 4),
        "confidence_before": current_conf,
        "confidence_after": new_conf,
        "delta": round(delta, 4),
        "source_projects": list(set(stats.get("projects", [])))[:5]
    })

    data["confidence"] = new_conf
    data["version"] = data.get("version", "0.6.0")
    parts = data["version"].split(".")
    if len(parts) >= 3:
        parts[2] = str(int(parts[2]) + 1)
        data["version"] = ".".join(parts)

    data["last_evolved"] = datetime.utcnow().isoformat() + "Z"
    return data

def update_index_from_usage(index_path, usage_stats, sidecars):
    if yaml is None:
        return None
    try:
        with open(index_path, "r") as f:
            index = yaml.safe_load(f)
    except Exception:
        return None

    changed = False
    for problem, data in index.get("by_dramatic_problem", {}).items():
        current_patterns = data.get("patterns", [])
        scored = []
        for pid in current_patterns:
            if pid in usage_stats and pid in sidecars:
                score = usage_stats[pid].get("success_signals", 0) + (sidecars[pid]["data"].get("confidence", 0.7) * 2)
                scored.append((pid, score))
        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            new_order = [p[0] for p in scored]
            if new_order != current_patterns:
                data["patterns"] = new_order
                changed = True

    if changed:
        with open(index_path, "w") as f:
            yaml.safe_dump(index, f, sort_keys=False)
        return "corpus-index.yaml updated with performance-based ordering"
    return None

def run_evolution(receipts_dir: str, outcomes_dir: str, patterns_dir: str = None, index_path: str = None) -> Dict:
    """Programmatic interface. Returns evolution receipt."""
    if patterns_dir is None:
        raise ValueError("patterns_dir is required for evolution")

    sidecars = load_all_sidecars(patterns_dir)
    usage = aggregate_usage(receipts_dir, outcomes_dir)

    evolved = []
    for pid, info in sidecars.items():
        updated = evolve_sidecar(info, usage)
        if updated:
            save_json(info["path"], updated)
            evolved.append(pid)

    index_msg = None
    if index_path:
        index_msg = update_index_from_usage(index_path, usage, sidecars)

    evolution_receipt = {
        "evolution_receipt": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "patterns_evolved": evolved,
            "index_update": index_msg,
            "usage_window": {
                "receipts_scanned": len(glob.glob(os.path.join(receipts_dir, "*"))),
                "outcomes_scanned": len(glob.glob(os.path.join(outcomes_dir, "*")))
            }
        }
    }

    return evolution_receipt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts-dir", required=True)
    parser.add_argument("--outcomes-dir", required=True)
    parser.add_argument("--patterns-dir", required=True)
    parser.add_argument("--index", help="Optional path to corpus-index.yaml to update")
    args = parser.parse_args()

    receipt = run_evolution(
        receipts_dir=args.receipts_dir,
        outcomes_dir=args.outcomes_dir,
        patterns_dir=args.patterns_dir,
        index_path=args.index
    )

    print(json.dumps(receipt, indent=2))

    if receipt["evolution_receipt"]["patterns_evolved"]:
        print(f"\nEvolved {len(receipt['evolution_receipt']['patterns_evolved'])} patterns.")
    else:
        print("\nNo patterns met evolution thresholds in this window.")

if __name__ == "__main__":
    main()
