#!/usr/bin/env python3
"""Automated handoff harness: paste/import → breakdown → export/API contract.

Verifies the product path a handoff user needs:
  1. Load Fountain/FDX fixtures (or stdin)
  2. Build shot-by-shot breakdown with continuity
  3. Assert machine-readable package shape
  4. Optional: hit REST endpoints via TestClient

Exit 0 on full pass. Use: ``make handoff`` or ``python scripts/handoff_harness.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "golden" / "fixtures"

REQUIRED_PACKAGE_KEYS = {
    "schema_version",
    "claim",
    "package_hash",
    "source_hash",
    "shots",
    "scenes",
    "entities",
    "setup_payoff_links",
    "shot_count",
    "scene_count",
    "entity_count",
}

REQUIRED_SHOT_KEYS = {
    "shot_id",
    "scene_id",
    "slugline",
    "label",
    "start_state_hash",
    "end_state_hash",
}


def _pass(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}")
    raise AssertionError(msg)


def run_kernel_suite(fixture_paths: list[Path]) -> list[dict[str, object]]:
    from continuity_forge_shots import (
        breakdown_to_markdown,
        build_breakdown_from_text,
    )

    packages: list[dict[str, object]] = []
    print("==> kernel: build_breakdown_from_text")
    for path in fixture_paths:
        text = path.read_text(encoding="utf-8")
        fmt = "fdx" if path.suffix.casefold() == ".fdx" else "fountain"
        package = build_breakdown_from_text(
            text,
            title=path.stem,
            document_key=f"handoff-{path.stem}",
            format=fmt,  # type: ignore[arg-type]
        )
        data = package.model_dump(mode="json")
        packages.append(data)

        missing = REQUIRED_PACKAGE_KEYS - set(data)
        if missing:
            _fail(f"{path.name}: missing package keys {sorted(missing)}")
        if data["schema_version"] != "cf.breakdown.v1":
            _fail(f"{path.name}: unexpected schema_version {data['schema_version']}")
        if "not_production" not in data["claim"] and "not_production_film" not in data["claim"]:
            _fail(f"{path.name}: claim must mark non-production: {data['claim']}")
        if data["shot_count"] < 1:
            _fail(f"{path.name}: expected ≥1 shot, got {data['shot_count']}")
        if data["scene_count"] != data["shot_count"]:
            # M2: one master shot per scene
            _fail(
                f"{path.name}: scene_count {data['scene_count']} != shot_count {data['shot_count']}"
            )
        if len(data["shots"]) != data["shot_count"]:
            _fail(f"{path.name}: shots list length mismatch")
        if not data["package_hash"] or len(data["package_hash"]) != 64:
            _fail(f"{path.name}: package_hash must be 64-char hex")

        for shot in data["shots"]:
            smiss = REQUIRED_SHOT_KEYS - set(shot)
            if smiss:
                _fail(f"{path.name}: shot missing {sorted(smiss)}")
            if not shot["slugline"]:
                _fail(f"{path.name}: empty slugline on shot")

        md = breakdown_to_markdown(package)
        if package.title not in md or "Shot-by-shot" not in md:
            _fail(f"{path.name}: markdown export incomplete")

        # Determinism: same input → same package_hash
        again = build_breakdown_from_text(
            text,
            title=path.stem,
            document_key=f"handoff-{path.stem}",
            format=fmt,  # type: ignore[arg-type]
        )
        if again.package_hash != package.package_hash:
            _fail(f"{path.name}: non-deterministic package_hash")

        _pass(
            f"{path.name}: {data['scene_count']} scenes · "
            f"{data['shot_count']} shots · "
            f"{data['entity_count']} entities · "
            f"{len(data['setup_payoff_links'])} setup/payoff"
        )
    return packages


def run_api_suite(fixture_paths: list[Path]) -> None:
    from continuity_forge_api.main import app
    from fastapi.testclient import TestClient

    print("==> api: POST /v1/breakdown (+ markdown)")
    client = TestClient(app)
    for path in fixture_paths:
        text = path.read_text(encoding="utf-8")
        fmt = "fdx" if path.suffix.casefold() == ".fdx" else "fountain"
        body = {
            "title": path.stem,
            "text": text,
            "document_key": f"api-handoff-{path.stem}",
            "format": fmt,
        }
        r = client.post("/v1/breakdown", json=body)
        if r.status_code != 200:
            _fail(f"API breakdown {path.name}: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        if data.get("shot_count", 0) < 1:
            _fail(f"API breakdown {path.name}: empty shots")
        if not data.get("package_hash"):
            _fail(f"API breakdown {path.name}: no package_hash")

        md = client.post("/v1/breakdown/markdown", json=body)
        if md.status_code != 200:
            _fail(f"API markdown {path.name}: HTTP {md.status_code}")
        payload = md.json()
        if "markdown" not in payload or payload["shot_count"] != data["shot_count"]:
            _fail(f"API markdown {path.name}: mismatch")
        _pass(f"REST {path.name}: breakdown + markdown ok")


def run_cli_suite(fixture: Path, out_dir: Path) -> None:
    import subprocess

    print("==> cli: continuity-forge breakdown")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "continuity_forge_compiler.cli",
        "breakdown",
        str(fixture),
        "--out",
        str(out_dir),
        "--document-key",
        f"cli-{fixture.stem}",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        _fail(f"CLI failed: {proc.stderr or proc.stdout}")
    json_path = out_dir / f"{fixture.stem}.breakdown.json"
    md_path = out_dir / f"{fixture.stem}.breakdown.md"
    if not json_path.is_file():
        _fail(f"CLI did not write {json_path}")
    if not md_path.is_file():
        _fail(f"CLI did not write {md_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if data.get("shot_count", 0) < 1:
        _fail("CLI package has no shots")
    _pass(f"CLI wrote {json_path.name} + {md_path.name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Continuity Forge handoff harness")
    parser.add_argument(
        "--fixtures",
        nargs="*",
        default=["continuity.fountain", "minimal.fountain"],
        help="Fixture filenames under tests/golden/fixtures",
    )
    parser.add_argument("--skip-api", action="store_true", help="Skip REST TestClient checks")
    parser.add_argument("--skip-cli", action="store_true", help="Skip CLI subprocess check")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "out" / "handoff-harness",
        help="CLI output directory",
    )
    args = parser.parse_args(argv)

    print("Continuity Forge handoff harness")
    print(f"Root: {ROOT}")
    paths: list[Path] = []
    for name in args.fixtures:
        p = FIXTURES / name if not Path(name).is_file() else Path(name)
        if not p.is_file():
            print(f"  FAIL  fixture not found: {p}")
            return 1
        paths.append(p)

    try:
        run_kernel_suite(paths)
        if not args.skip_api:
            run_api_suite(paths)
        if not args.skip_cli:
            run_cli_suite(paths[0], args.out)
    except AssertionError as exc:
        print()
        print(f"Handoff harness FAILED: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface unexpected errors to operator
        print()
        print(f"Handoff harness ERROR: {exc}")
        return 1

    print()
    print("Handoff harness: PASS")
    print("  Product path verified: paste/import → shot breakdown + continuity → JSON/MD/API")
    print("  Claim remains non-production film.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
