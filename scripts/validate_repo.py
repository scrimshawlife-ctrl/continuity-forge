"""Durable Continuity Forge repo validation (Phase 2+).

Runs the M0 gate suite, then enforces **per-path** coverage floors for critical
modules. No arbitrary repo-wide coverage percentage — only named critical paths.

Thresholds are deliberately set slightly below measured coverage so the gate is
achievable; raise them as suites deepen.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class CoverageFloor:
    """Per-path coverage floor (coverage.py --include + --fail-under)."""

    name: str
    # Shell-style patterns for coverage report --include (comma-separated).
    include: str
    fail_under: int
    # Measured baseline when floors were set (documentation only).
    measured_pct: float


# Achievable floors from 2026-07-28 full-suite measurement (pytest --cov).
# auth ~83%, operator ~85%, harness pipeline+store ~94%, repair ~94%.
CRITICAL_COVERAGE_FLOORS: tuple[CoverageFloor, ...] = (
    CoverageFloor(
        name="packages/auth",
        include="*/continuity_forge_auth/*",
        fail_under=80,
        measured_pct=82.8,
    ),
    CoverageFloor(
        name="packages/operator (mutation/lease)",
        include="*/continuity_forge_operator/*",
        fail_under=80,
        measured_pct=85.3,
    ),
    CoverageFloor(
        name="packages/harness pipeline+store",
        include=("*/continuity_forge_harness/pipeline.py,*/continuity_forge_harness/store.py"),
        fail_under=90,
        measured_pct=93.8,
    ),
    CoverageFloor(
        name="packages/repair",
        include="*/continuity_forge_repair/*",
        fail_under=90,
        measured_pct=94.2,
    ),
)

LINT_GATES = (
    Gate("ruff", (sys.executable, "-m", "ruff", "check", ".")),
    Gate("ruff-format", (sys.executable, "-m", "ruff", "format", "--check", ".")),
    Gate("mypy", (sys.executable, "-m", "mypy", "packages", "apps", "scripts")),
)

# Full-tree coverage collection only — no global --cov-fail-under.
PYTEST_COV_GATE = Gate(
    "pytest",
    (
        sys.executable,
        "-m",
        "pytest",
        "--cov=packages",
        "--cov=apps",
        "--cov-report=term-missing",
    ),
)


def run_gate(gate: Gate) -> None:
    print(f"\n==> {gate.name}: {' '.join(gate.command)}", flush=True)
    completed = subprocess.run(gate.command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        print(f"Repo validation FAILED at gate: {gate.name}", file=sys.stderr)
        raise SystemExit(completed.returncode)


def check_critical_coverage_floors() -> None:
    """Enforce per-path coverage floors against the latest .coverage data file."""
    print("\n==> coverage-floors (critical modules, per-path)", flush=True)
    print(
        "  (no global %; floors measured against current suite, then set slightly under)",
        flush=True,
    )
    data_file = ROOT / ".coverage"
    if not data_file.exists():
        print(
            "Repo validation FAILED at gate: coverage-floors "
            "(missing .coverage — run pytest --cov first)",
            file=sys.stderr,
        )
        raise SystemExit(2)

    failures: list[str] = []
    for floor in CRITICAL_COVERAGE_FLOORS:
        cmd = (
            sys.executable,
            "-m",
            "coverage",
            "report",
            f"--include={floor.include}",
            f"--fail-under={floor.fail_under}",
            "--precision=1",
            "--show-missing",
        )
        print(
            f"\n  -- {floor.name}: fail-under={floor.fail_under}% "
            f"(measured baseline ~{floor.measured_pct}%)",
            flush=True,
        )
        print(f"     include={floor.include}", flush=True)
        completed = subprocess.run(cmd, cwd=ROOT, check=False)
        if completed.returncode != 0:
            failures.append(
                f"{floor.name}: below {floor.fail_under}% (coverage exit {completed.returncode})"
            )

    if failures:
        print("\nCritical coverage floor FAILURES:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        print("Repo validation FAILED at gate: coverage-floors", file=sys.stderr)
        raise SystemExit(2)

    print("\n  All critical coverage floors: PASS", flush=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Continuity Forge durable repo validation (M0 + coverage floors)"
    )
    parser.add_argument(
        "--floors-only",
        action="store_true",
        help="Only check per-path coverage floors (requires existing .coverage)",
    )
    parser.add_argument(
        "--skip-lint",
        action="store_true",
        help="Skip ruff/mypy (still run pytest + floors unless --floors-only)",
    )
    args = parser.parse_args(argv)

    print(f"Continuity Forge repo validation root: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")

    if args.floors_only:
        check_critical_coverage_floors()
        print("\nRepo validation (floors-only): PASS")
        return

    if not args.skip_lint:
        for gate in LINT_GATES:
            run_gate(gate)

    run_gate(PYTEST_COV_GATE)
    check_critical_coverage_floors()
    print("\nRepo validation: PASS")


if __name__ == "__main__":
    main()
