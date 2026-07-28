"""Canonical local/CI gate for Continuity Forge kernel validation (M0+).

Includes Phase 2 per-path coverage floors for critical modules (via
``scripts/validate_repo.py --floors-only`` after pytest collects coverage).
There is no arbitrary global coverage percentage.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]


GATES = (
    Gate("ruff", (sys.executable, "-m", "ruff", "check", ".")),
    Gate("ruff-format", (sys.executable, "-m", "ruff", "format", "--check", ".")),
    Gate("mypy", (sys.executable, "-m", "mypy", "packages", "apps", "scripts")),
    Gate(
        "pytest",
        (
            sys.executable,
            "-m",
            "pytest",
            "--cov=packages",
            "--cov=apps",
            "--cov-report=term-missing",
            # No global --cov-fail-under. Critical paths are checked next.
        ),
    ),
    Gate(
        "coverage-floors",
        (
            sys.executable,
            str(ROOT / "scripts" / "validate_repo.py"),
            "--floors-only",
        ),
    ),
    # Handoff product path: paste/import → breakdown JSON/MD/API/CLI
    Gate(
        "handoff",
        (sys.executable, str(ROOT / "scripts" / "handoff_harness.py")),
    ),
)


def run_gate(gate: Gate) -> None:
    print(f"\n==> {gate.name}: {' '.join(gate.command)}", flush=True)
    completed = subprocess.run(gate.command, cwd=ROOT, check=False)
    if completed.returncode != 0:
        print(f"M0 validation FAILED at gate: {gate.name}", file=sys.stderr)
        raise SystemExit(completed.returncode)


def main() -> None:
    print(f"Continuity Forge M0 validation root: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    for gate in GATES:
        run_gate(gate)
    print("\nM0 validation: PASS")


if __name__ == "__main__":
    main()
