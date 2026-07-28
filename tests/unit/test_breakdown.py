"""Unit tests for shot breakdown handoff package."""

from __future__ import annotations

from pathlib import Path

from continuity_forge_shots import (
    breakdown_to_markdown,
    build_breakdown_from_text,
)

FIXTURE = Path(__file__).parents[1] / "golden" / "fixtures" / "continuity.fountain"
MINIMAL = Path(__file__).parents[1] / "golden" / "fixtures" / "minimal.fountain"


def test_breakdown_continuity_fixture_has_shots_and_entities() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    pkg = build_breakdown_from_text(text, title="Continuity", document_key="bd-1")
    assert pkg.schema_version == "cf.breakdown.v1"
    assert pkg.claim == "shot_breakdown_with_continuity_not_production_film"
    assert pkg.shot_count >= 1
    assert pkg.scene_count == pkg.shot_count
    assert pkg.entity_count >= 1
    assert pkg.package_hash
    assert all(s.slugline for s in pkg.shots)
    assert pkg.shots[0].start_state_hash
    # Continuity sample should surface setup/payoff for keycard path
    assert len(pkg.setup_payoff_links) >= 1


def test_breakdown_deterministic() -> None:
    text = MINIMAL.read_text(encoding="utf-8")
    a = build_breakdown_from_text(text, title="Min", document_key="bd-d")
    b = build_breakdown_from_text(text, title="Min", document_key="bd-d")
    assert a.package_hash == b.package_hash
    assert a.model_dump(mode="json") == b.model_dump(mode="json")


def test_breakdown_markdown_export() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    pkg = build_breakdown_from_text(text, title="MD", document_key="bd-md")
    md = breakdown_to_markdown(pkg)
    assert "# MD" in md
    assert "Shot-by-shot breakdown" in md
    assert "not production" in md.lower() or "Not production" in md
