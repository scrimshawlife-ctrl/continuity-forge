#!/usr/bin/env python3
"""Validate Kubrick esoteric-encoding YAML/JSON and enforce semantic gates."""

import argparse
import json
import os
import sys
from typing import Dict, List

try:
    import yaml
except ImportError:
    print("pyyaml required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft202012Validator
except ImportError:
    print("jsonschema required. pip install jsonschema", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
SCHEMA_PATH = os.path.join(SKILL_ROOT, "schemas", "esoteric-encoding.schema.yaml")


def load_data(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle) if path.endswith(".json") else yaml.safe_load(handle)


def semantic_errors(payload: Dict) -> List[str]:
    errors: List[str] = []
    selections = payload.get("selections", [])
    if len(selections) > 3:
        errors.append("selection density exceeds one primary plus two secondary concepts")

    traditions = {item.get("tradition") for item in selections if item.get("tradition")}
    if len(traditions) > 1:
        boundaries = [item.get("tradition_boundary", "").strip() for item in selections]
        if not all(boundaries):
            errors.append("cross-tradition selection lacks explicit boundaries")

    for index, item in enumerate(selections):
        if not item.get("observable_evidence"):
            errors.append(f"selection[{index}] lacks observable evidence")
        if not item.get("mutation_rule"):
            errors.append(f"selection[{index}] lacks recurrence mutation rule")
        if not item.get("provenance"):
            errors.append(f"selection[{index}] lacks provenance")

    validation = payload.get("validation", {})
    for gate, result in validation.get("anti_slop_gates", {}).items():
        if result.get("status") == "FAIL":
            errors.append(f"anti-slop gate {gate} failed")

    if payload.get("canon_status") == "LOCKED" and not payload.get("forge_handoff"):
        errors.append("LOCKED output requires Forge handoff mutation metadata")

    return errors


def validate(payload: Dict) -> List[str]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
        schema = yaml.safe_load(handle)
    validator = Draft202012Validator(schema)
    errors = [
        f"schema:{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    ]
    errors.extend(f"semantic:{message}" for message in semantic_errors(payload))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="YAML or JSON esoteric encoding payload")
    args = parser.parse_args()

    payload = load_data(args.path)
    errors = validate(payload)
    result = {
        "status": "PASS" if not errors else "FAIL",
        "schema": "esoteric-encoding.schema.yaml",
        "errors": errors,
    }
    print(yaml.safe_dump(result, sort_keys=False))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
