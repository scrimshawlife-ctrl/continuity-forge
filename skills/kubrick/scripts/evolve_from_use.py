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
import hashlib
import copy
import json
import os
import glob
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
import tempfile
import uuid

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
                if Path(path).is_symlink():
                    raise ValueError("sidecar symlink is not allowed")
                data = load_json(path)
                sidecars[data.get("pattern_id", fname)] = {"path": path, "data": data}
    return sidecars


def aggregate_usage(receipts_dir, outcomes_dir, consumed=None):
    """Content-address events, not filenames; never silently ignore malformed evidence."""
    usage = defaultdict(lambda: {"events": {}})
    seen = dict(consumed or {})
    for directory, kind in ((receipts_dir, "retrieval"), (outcomes_dir, "outcome")):
        for path in sorted(
            glob.glob(os.path.join(directory, "*.json"))
            + glob.glob(os.path.join(directory, "*.yaml"))
        ):
            if path.endswith(".json"):
                record = load_json(path)
            else:
                if yaml is None:
                    raise ValueError("PyYAML is required to read YAML evidence")
                with open(path) as stream:
                    record = yaml.safe_load(stream)
            rec = record.get("retrieval_receipt", record) if kind == "retrieval" else record
            identity = rec.get("event_id") or (
                rec.get("request_hash")
                if kind == "retrieval"
                else [rec.get("project"), rec.get("pattern_id")]
            )
            if not identity or identity == [None, rec.get("pattern_id")]:
                raise ValueError("evidence requires event_id or request_hash/project identity")
            event_id = hashlib.sha256(
                json.dumps([kind, identity], sort_keys=True).encode()
            ).hexdigest()
            content = {k: v for k, v in rec.items() if k not in ("timestamp", "metadata", "date")}
            digest = hashlib.sha256(
                json.dumps(content, sort_keys=True, allow_nan=False).encode()
            ).hexdigest()
            if event_id in seen and seen[event_id] != digest:
                raise ValueError("conflicting evidence for stable identity")
            seen[event_id] = digest
            if kind == "retrieval":
                for item in rec.get("ranked_patterns", [])[:3]:
                    pid = item["pattern_id"]
                    score = item.get("total_score", 0.5)
                    if type(score) not in (int, float):
                        raise ValueError("retrieval score must be numeric, not coerced")
                    if not 0 <= score <= 1:
                        raise ValueError("retrieval score must be finite and in [0, 1]")
                    usage[pid]["events"][event_id] = {
                        "evidence_hash": digest,
                        "uses": 1,
                        "total_score": score,
                        "projects": [rec.get("request_hash", "unknown")],
                    }
            else:
                pid = rec["pattern_id"]
                signal = rec.get("outcome", "neutral")
                if signal not in (
                    "success",
                    "failure",
                    "debt",
                    "collision",
                    "revision_broken",
                    "neutral",
                ):
                    raise ValueError("unknown outcome signal")
                usage[pid]["events"][event_id] = {
                    "evidence_hash": digest,
                    "success_signals": int(signal == "success"),
                    "failure_signals": int(
                        signal in ("failure", "debt", "collision", "revision_broken")
                    ),
                    "projects": [rec.get("project", "unknown")],
                }
    return dict(usage)


def evolve_sidecar(sidecar_info, usage_stats):
    data = copy.deepcopy(sidecar_info["data"])
    stats = usage_stats.get(data["pattern_id"], {})
    if not stats:
        return None
    # Legacy aggregate callers get exact-window dedupe. File-based callers use event IDs.
    incoming = stats.get("events")
    if incoming is None:
        key = hashlib.sha256(
            json.dumps(stats, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
        incoming = {key: stats}
    events = data.get("evolution_events", {})
    for key in set(incoming) & set(events):
        if incoming[key] != events[key]:
            raise ValueError("conflicting consumed evidence for stable identity")
    if not set(incoming) - set(events):
        return None
    events.update(incoming)
    uses = sum(e.get("uses", 0) for e in events.values())
    if not uses:
        return None  # outcomes are applied once there is actual retrieval evidence
    avg_score = sum(e.get("total_score", 0) for e in events.values()) / uses
    success = sum(e.get("success_signals", 0) for e in events.values())
    failure = sum(e.get("failure_signals", 0) for e in events.values())
    success_rate = success / (success + failure) if success + failure else 0.5
    current = data.get("confidence", 0.7)
    baseline = data.get("evolution_baseline_confidence", current)
    delta = 0.0
    if uses >= 3:
        delta += (avg_score - 0.6) * 0.15 + (success_rate - 0.5) * 0.25
    if failure > success and uses >= 2:
        delta -= 0.1
    confidence = max(0.3, min(0.98, round(baseline + delta, 4)))
    now = datetime.now(timezone.utc).isoformat()
    data.setdefault("usage_history", []).append(
        {
            "date": now,
            "uses_in_window": uses,
            "avg_retrieval_score": round(avg_score, 4),
            "success_rate": round(success_rate, 4),
            "confidence_before": current,
            "confidence_after": confidence,
            "delta": round(confidence - current, 4),
            "source_projects": sorted({p for e in events.values() for p in e.get("projects", [])})[
                :5
            ],
        }
    )
    data["evolution_events"] = events
    data["evolution_baseline_confidence"] = baseline
    data["confidence"] = confidence
    parts = data.get("version", "0.6.0").split(".")
    if len(parts) == 3:
        parts[2] = str(int(parts[2]) + 1)
    data["version"] = ".".join(parts)
    data["last_evolved"] = now
    return data


def update_index_from_usage(index_path, usage_stats, sidecars, dry_run=False):
    if yaml is None:
        raise ValueError("PyYAML is required for index evolution")
    with open(index_path) as stream:
        index = yaml.safe_load(stream)
    changed = False
    for data in index.get("by_dramatic_problem", {}).values():
        current = data.get("patterns", [])
        scored = []
        for pid in current:
            if pid in usage_stats and pid in sidecars:
                info = sidecars[pid]["data"]
                success = sum(
                    e.get("success_signals", 0) for e in info.get("evolution_events", {}).values()
                )
                scored.append((pid, success + info.get("confidence", 0.7) * 2))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        ranked = iter(pid for pid, _ in scored)
        scored_ids = {pid for pid, _ in scored}
        order = [next(ranked) if pid in scored_ids else pid for pid in current]
        if order != current:
            data["patterns"] = order
            changed = True
    if not changed:
        return None
    text = yaml.safe_dump(index, sort_keys=False)
    if not dry_run:
        Path(index_path).write_text(text)
    return text


def run_evolution(
    receipts_dir,
    outcomes_dir,
    patterns_dir=None,
    index_path=None,
    dry_run=True,
    expected_plan_hash=None,
):
    """Plan by default. Explicit apply stages all files and rolls back caught I/O failures."""
    if patterns_dir is None or not Path(patterns_dir).is_dir():
        raise ValueError("patterns_dir must be an existing project-owned corpus directory")
    for directory in (receipts_dir, outcomes_dir):
        if not Path(directory).is_dir():
            raise ValueError("evidence directories must exist (empty is allowed)")
    root = Path(patterns_dir).resolve()
    lock = root / ".evolution.lock"
    recovery_required = False
    if not dry_run:
        lock.mkdir()  # single-writer guard; stale lock requires human recovery

    def input_hash():
        paths = list(root.rglob("*.json"))
        for directory in (receipts_dir, outcomes_dir):
            paths.extend(Path(directory).glob("*.json"))
            paths.extend(Path(directory).glob("*.yaml"))
        if index_path:
            paths.append(Path(index_path))
        paths.append(Path(__file__))
        items = [
            (str(path.absolute()), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(set(paths))
        ]
        return hashlib.sha256(json.dumps(items).encode()).hexdigest()

    try:
        plan_hash = input_hash()
        if expected_plan_hash is not None and expected_plan_hash != plan_hash:
            raise ValueError("stale evolution plan; review a new dry-run")
        sidecars = load_all_sidecars(root)
        consumed = {}
        for info in sidecars.values():
            for event_id, event in info["data"].get("evolution_events", {}).items():
                digest = event.get("evidence_hash")
                if digest is None:  # legacy aggregate events have no evidence hash
                    continue
                if event_id in consumed and consumed[event_id] != digest:
                    raise ValueError("conflicting consumed evidence for stable identity")
                consumed[event_id] = digest
        usage = aggregate_usage(receipts_dir, outcomes_dir, consumed)
        if set(usage) - set(sidecars):
            raise ValueError(
                "unknown pattern in evidence: " + ", ".join(sorted(set(usage) - set(sidecars)))
            )
        from jsonschema import Draft7Validator

        schema_path = Path(__file__).with_name("symbolic-narrative-pattern.schema.json")
        if not schema_path.exists():
            schema_path = (
                Path(__file__).resolve().parents[1]
                / "schemas/symbolic-narrative-pattern.schema.json"
            )
        validator = Draft7Validator(load_json(schema_path))
        changes = {}
        evolved = []
        for pid, info in sidecars.items():
            updated = evolve_sidecar(info, usage)
            if updated:
                validator.validate(updated)
                info["data"] = updated
                changes[Path(info["path"])] = json.dumps(
                    updated, indent=2, allow_nan=False
                ).encode()
                evolved.append(pid)
        index_text = (
            update_index_from_usage(index_path, usage, sidecars, dry_run=True)
            if index_path
            else None
        )
        if index_text is not None:
            changes[Path(index_path)] = index_text.encode()
        receipt = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patterns_evolved": evolved,
            "dry_run": dry_run,
            "plan_hash": plan_hash,
            "index_update": index_text is not None,
            "changes": [
                {
                    "path": str(path.resolve()),
                    "before_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "after_sha256": hashlib.sha256(value).hexdigest(),
                }
                for path, value in changes.items()
            ],
        }
        result = {"evolution_receipt": receipt}
        if input_hash() != plan_hash:
            raise ValueError("stale inputs changed during planning")
        if changes and not dry_run:
            receipt_path = root.parent / ("evolution-" + uuid.uuid4().hex + ".json")
            receipt["receipt_path"] = str(receipt_path)
            # Include exact prior contents for manual recovery after a process/host crash.
            receipt["before_contents"] = {str(path.resolve()): path.read_text() for path in changes}
            changes[receipt_path] = json.dumps(result, indent=2, allow_nan=False).encode()
            originals = {path: path.read_bytes() if path.exists() else None for path in changes}
            staged = {}
            applied = []
            try:
                for path, value in changes.items():
                    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                        staged[path] = Path(stream.name)
                        stream.write(value)
                        stream.flush()
                        os.fsync(stream.fileno())
                if input_hash() != plan_hash:
                    raise ValueError("stale inputs changed during staging")
                # Persist provenance before touching corpus; success is returned only after read-back.
                order = [receipt_path] + [p for p in changes if p != receipt_path]
                for path in order:
                    os.replace(staged[path], path)
                    applied.append(path)
                for path, value in changes.items():
                    if path.read_bytes() != value:
                        raise OSError("evolution read-back mismatch")
            except Exception as apply_error:
                rollback_errors = []
                for path in reversed(applied):
                    if path == receipt_path:
                        continue  # retain provenance until every corpus restore is verified
                    backup = None
                    original = originals[path]
                    try:
                        if original is None:
                            path.unlink()
                        else:
                            try:
                                with tempfile.NamedTemporaryFile(
                                    dir=path.parent, delete=False
                                ) as stream:
                                    backup = Path(stream.name)
                                    stream.write(original)
                                os.replace(backup, path)
                                if path.read_bytes() != original:
                                    raise OSError("rollback read-back mismatch")
                            finally:
                                if backup is not None:
                                    backup.unlink(missing_ok=True)
                    except Exception as restore_error:  # noqa: BLE001 - report all failures
                        rollback_errors.append(f"{path}: {restore_error!r}")
                if not rollback_errors and receipt_path in applied:
                    try:
                        receipt_path.unlink()
                    except Exception as restore_error:  # noqa: BLE001 - report all failures
                        rollback_errors.append(f"{receipt_path}: {restore_error!r}")
                if rollback_errors:
                    recovery_required = True
                    raise RuntimeError(
                        f"evolution apply failed: {apply_error!r}; rollback failed: "
                        + "; ".join(rollback_errors)
                        + f"; manual recovery required using {receipt_path}; lock retained at {lock}"
                    ) from apply_error
                raise
            finally:
                for temp in staged.values():
                    temp.unlink(missing_ok=True)
        return result
    finally:
        if not dry_run and not recovery_required:
            lock.rmdir()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts-dir", required=True)
    parser.add_argument("--outcomes-dir", required=True)
    parser.add_argument("--patterns-dir", required=True)
    parser.add_argument("--index", help="Optional path to corpus-index.yaml to update")
    parser.add_argument(
        "--expected-plan-hash", help="Reject apply if reviewed dry-run inputs changed"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Plan only (default); zero writes")
    mode.add_argument(
        "--apply", action="store_true", help="Explicitly apply reviewed local corpus changes"
    )
    args = parser.parse_args()

    receipt = run_evolution(
        receipts_dir=args.receipts_dir,
        outcomes_dir=args.outcomes_dir,
        patterns_dir=args.patterns_dir,
        index_path=args.index,
        dry_run=not args.apply,
        expected_plan_hash=args.expected_plan_hash,
    )

    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
