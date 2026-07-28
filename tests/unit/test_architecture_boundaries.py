"""Architecture / import-boundary tests for Continuity Forge trust edges.

Providers generate PROPOSED media only. They must never import persistence
repositories or reach into canonical stores.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDERS_SRC = REPO_ROOT / "packages" / "providers" / "src" / "continuity_forge_providers"
PERSISTENCE_PKG = "continuity_forge_persistence"
OPERATOR_STORE_NAMES = {
    "ProjectStore",
    "FileProjectStore",
    "DEFAULT_PROJECT_STORE",
}


def _python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def _imports_from_module(path: Path) -> list[tuple[str, str | None]]:
    """Return (module, imported_name|None) pairs from import statements."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name, None))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                found.append((module, alias.name))
    return found


def _is_operator_module(module: str) -> bool:
    return module == "continuity_forge_operator" or module.startswith("continuity_forge_operator.")


def test_providers_must_not_import_persistence_repositories() -> None:
    """packages/providers must not import continuity_forge_persistence.

    Failure means a provider worker reached into durable repositories —
    a trust-boundary violation (models generate PROPOSED only).
    """
    assert PROVIDERS_SRC.is_dir(), f"providers package missing at {PROVIDERS_SRC}"

    violations: list[str] = []
    for path in _python_files(PROVIDERS_SRC):
        for module, name in _imports_from_module(path):
            if module == PERSISTENCE_PKG or module.startswith(f"{PERSISTENCE_PKG}."):
                rel = path.relative_to(REPO_ROOT)
                detail = f"{module}.{name}" if name else module
                violations.append(f"{rel}: imports {detail}")

    assert not violations, (
        "Architecture boundary violation: packages/providers must not import "
        "persistence repositories (continuity_forge_persistence). "
        "Providers emit PROPOSED candidates only; the operator/runtime owns "
        "canonical writes via MutationEnvelope + ProjectStore. "
        "Offending imports:\n  - " + "\n  - ".join(violations)
    )


def test_providers_must_not_import_operator_project_store() -> None:
    """Providers must not pull ProjectStore / FileProjectStore for direct writes."""
    violations: list[str] = []
    for path in _python_files(PROVIDERS_SRC):
        for module, name in _imports_from_module(path):
            # Flag bare package import or explicit ProjectStore symbols only.
            if _is_operator_module(module) and (name is None or name in OPERATOR_STORE_NAMES):
                rel = path.relative_to(REPO_ROOT)
                detail = f"{module}.{name}" if name else module
                violations.append(f"{rel}: imports {detail}")

    assert not violations, (
        "Architecture boundary violation: packages/providers must not import "
        "operator ProjectStore symbols. Canon writes go through API/MCP + "
        "MutationEnvelope, never from model workers. "
        "Offending imports:\n  - " + "\n  - ".join(violations)
    )


def test_providers_source_has_no_persistence_string_imports() -> None:
    """Defense-in-depth: forbid string forms that bypass static import graphs."""
    needle = "continuity_forge_persistence"
    hits: list[str] = []
    for path in _python_files(PROVIDERS_SRC):
        text = path.read_text(encoding="utf-8")
        if needle in text:
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, (
        "Architecture boundary violation: packages/providers source references "
        f"{needle!r} (repositories must stay behind the operator boundary). "
        f"Files: {', '.join(hits)}"
    )
