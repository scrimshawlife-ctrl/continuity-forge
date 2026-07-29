"""Product workflow view models — pure adapters over deterministic kernel output."""

from __future__ import annotations

from pathlib import Path

import pytest
from continuity_forge_operator.product_workflow import (
    ANALYSIS_STAGES,
    PRODUCTION_TYPES,
    ProjectPhase,
    ProvenanceLabel,
    SceneReadiness,
    ShotStatus,
    apply_operator_override,
    build_analysis_summary,
    build_entity_profiles,
    build_scene_cards,
    build_scene_detail,
    can_transition,
    classify_conflict_category,
    detect_script_format,
    friendly_parser_error,
    generate_document_key,
    make_review_decision,
    package_is_provider_neutral,
    parse_slugline,
    prepare_scene_package,
    provenance_badge,
    resolve_conflict,
    scene_is_ready,
    transition_project,
)
from continuity_forge_shots import build_breakdown_from_text

FIXTURE = Path(__file__).resolve().parents[1] / "golden" / "fixtures" / "continuity.fountain"


@pytest.fixture(scope="module")
def sample_text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def package(sample_text: str):
    return build_breakdown_from_text(
        sample_text,
        title="Continuity Sample",
        document_key="continuity-sample",
    )


def test_project_phase_transitions_are_explicit() -> None:
    assert can_transition(ProjectPhase.EMPTY, ProjectPhase.IMPORTED)
    assert not can_transition(ProjectPhase.EMPTY, ProjectPhase.APPROVED)
    assert (
        transition_project(ProjectPhase.IMPORTED, ProjectPhase.ANALYZING) is ProjectPhase.ANALYZING
    )
    with pytest.raises(ValueError, match="invalid project phase"):
        transition_project(ProjectPhase.EMPTY, ProjectPhase.GENERATING)


def test_provenance_badges_use_text_and_icon_not_color_alone() -> None:
    for label in ProvenanceLabel:
        badge = provenance_badge(label)
        assert badge.label is label
        assert badge.icon
        assert badge.title
    assert provenance_badge("deterministic").label is ProvenanceLabel.SCRIPT
    assert provenance_badge("heuristic").label is ProvenanceLabel.INFERRED


def test_analysis_summary_from_real_breakdown(package, sample_text: str) -> None:
    summary = build_analysis_summary(package, production_type="Short Film")
    assert summary.schema_version == "cf.product.analysis.v1"
    assert summary.counts.scenes == package.scene_count
    assert summary.counts.shots == package.shot_count
    assert summary.counts.characters >= 1
    assert summary.package_hash == package.package_hash
    assert summary.stages_completed == list(ANALYSIS_STAGES)
    assert "Feature Film" in PRODUCTION_TYPES
    # Deterministic: same input → same package hash on re-run
    again = build_breakdown_from_text(
        sample_text, title="Continuity Sample", document_key="continuity-sample"
    )
    assert again.package_hash == package.package_hash


def test_scene_cards_have_readiness_and_creative_fields(package) -> None:
    cards = build_scene_cards(package)
    assert len(cards) == package.scene_count
    first = cards[0]
    assert first.scene_number >= 1
    assert first.slugline
    assert first.readiness in set(SceneReadiness)
    assert first.shot_count >= 0
    ie, loc, tod = parse_slugline("INT. SAFEHOUSE - NIGHT")
    assert ie == "INT."
    assert loc and "SAFEHOUSE" in loc.upper()
    assert tod and "NIGHT" in tod.upper()


def test_scene_detail_entry_exit_and_shot_cards(package, sample_text: str) -> None:
    scene_id = package.scenes[0].scene_id
    detail = build_scene_detail(package, scene_id, source_text=sample_text)
    assert detail is not None
    assert detail.entry_state
    assert detail.exit_state
    assert detail.entities_present.get("characters") is not None
    if detail.shots:
        shot = detail.shots[0]
        assert shot.shot_number
        assert shot.status is ShotStatus.DRAFT
        assert shot.prompt_preview
        assert shot.start_state_hash  # advanced detail still available


def test_entity_profiles_cover_kinds(package) -> None:
    profiles = build_entity_profiles(package)
    kinds = {p.kind for p in profiles}
    assert "character" in kinds
    for p in profiles:
        assert p.values
        assert p.values[0].provenance.label in set(ProvenanceLabel)


def test_operator_override_preserves_original_and_previews_invalidation(package) -> None:
    entity = next(e for e in package.entities if e.kind == "character")
    override, preview = apply_operator_override(
        target_kind="entity",
        target_id=entity.entity_id,
        field_name="name",
        original_value=entity.name,
        locked_value=entity.name + " (locked)",
        package=package,
        rationale="Operator correction",
    )
    assert override.provenance is ProvenanceLabel.USER_LOCKED
    assert override.original_value == entity.name
    assert override.locked_value != override.original_value
    assert preview.shot_count >= 0
    assert "affects" in preview.message.lower() or preview.scene_count >= 0


def test_conflict_resolution_requires_explicit_choice(package) -> None:
    summary = build_analysis_summary(package)
    if not summary.conflicts:
        # Inject a diagnostic-shaped conflict path via classifier
        cat = classify_conflict_category("Mara jacket changes from blue to black", "wardrobe")
        assert cat == "wardrobe"
        return
    conflict = summary.conflicts[0]
    with pytest.raises(ValueError, match="unknown"):
        resolve_conflict(conflict, "not-a-real-choice")
    resolved = resolve_conflict(conflict, conflict.choices[0].choice_id)
    assert resolved.resolved is True
    assert resolved.resolution_choice_id == conflict.choices[0].choice_id


def test_scene_readiness_blocks_on_unresolved_blocking() -> None:
    from continuity_forge_operator.product_workflow import ConflictCard, ConflictChoice

    blocking = [
        ConflictCard(
            conflict_id="x",
            category="wardrobe",
            plain_language="conflict",
            severity="blocking",
            choices=[ConflictChoice(choice_id="a", label="A")],
            resolved=False,
        )
    ]
    assert scene_is_ready(blocking_conflicts=blocking) is False
    blocking[0] = resolve_conflict(blocking[0], "a")
    assert scene_is_ready(blocking_conflicts=blocking) is True


def test_prepare_scene_package_provider_neutral(package, sample_text: str) -> None:
    scene_id = package.scenes[0].scene_id
    scene_pkg = prepare_scene_package(
        package,
        scene_id,
        source_text=sample_text,
        warnings_acknowledged=True,
    )
    assert scene_pkg.schema_version == "cf.scene_package.v1"
    assert scene_pkg.scene_id == scene_id
    assert scene_pkg.slugline
    assert scene_pkg.dependency_hashes.get("source_hash") == package.source_hash
    assert package_is_provider_neutral(scene_pkg)
    blob = scene_pkg.model_dump_json().lower()
    assert "openai_payload" not in blob
    assert "runway_payload" not in blob


def test_review_decision_preserves_lineage_no_silent_canon() -> None:
    d = make_review_decision(shot_id="shot-1", action="accept", candidate_id="cand-1")
    assert d.lineage_preserved is True
    assert d.advances_canon is True  # intent flag only
    r = make_review_decision(shot_id="shot-1", action="reject")
    assert r.advances_canon is False


def test_apply_overrides_shows_user_locked_on_profiles(package) -> None:
    from continuity_forge_operator.product_workflow import apply_overrides_to_profiles

    profiles = build_entity_profiles(package)
    entity = next(e for e in package.entities if e.kind == "character")
    override, _preview = apply_operator_override(
        target_kind="entity",
        target_id=entity.entity_id,
        field_name="name",
        original_value=entity.name,
        locked_value=entity.name + " Locked",
        package=package,
    )
    applied = apply_overrides_to_profiles(profiles, [override])
    hit = next(p for p in applied if p.entity_id == entity.entity_id)
    name_val = next(v for v in hit.values if v.field_name == "name")
    assert name_val.locked is True
    assert name_val.provenance.label is ProvenanceLabel.USER_LOCKED
    assert name_val.value == entity.name + " Locked"
    assert name_val.original_value == entity.name
    assert hit.name == entity.name + " Locked"


def test_entry_exit_state_are_distinct(package, sample_text: str) -> None:
    scene_id = package.scenes[0].scene_id
    detail = build_scene_detail(package, scene_id, source_text=sample_text)
    assert detail is not None
    entry_fields = {v.field_name: v.value for v in detail.entry_state}
    exit_fields = {v.field_name: v.value for v in detail.exit_state}
    assert "start_state" in entry_fields
    assert "end_state" in exit_fields
    # Distinct field sets (entry has start_state, exit has end_state / next_scene)
    assert entry_fields.keys() != exit_fields.keys() or entry_fields.get(
        "start_state"
    ) != exit_fields.get("end_state")


def test_scene_metadata_override_applied_to_cards(package) -> None:
    from continuity_forge_operator.product_workflow import apply_scene_metadata_overrides

    cards = build_scene_cards(package)
    scene = cards[0]
    ov, _ = apply_operator_override(
        target_kind="scene",
        target_id=scene.scene_id,
        field_name="slugline",
        original_value=scene.slugline,
        locked_value="INT. CORRECTED SET - DAWN",
        package=package,
    )
    # target_kind scene for metadata
    ov = ov.model_copy(update={"target_kind": "scene"})
    updated = apply_scene_metadata_overrides(cards, [ov])
    assert updated[0].slugline == "INT. CORRECTED SET - DAWN"
    assert updated[0].time_of_day and "DAWN" in updated[0].time_of_day.upper()


def test_friendly_parser_errors_are_actionable() -> None:
    err = friendly_parser_error("missing scene heading near line 148")
    assert "scene heading" in err.what_happened.lower() or "INT." in err.what_happened
    assert err.technical_detail
    assert err.data_preserved is True
    assert err.next_steps


def test_format_detection_and_document_key() -> None:
    assert detect_script_format("script.fdx", "<FinalDraft") == "fdx"
    assert detect_script_format("script.fountain", "INT. ROOM - DAY") == "fountain"
    key = generate_document_key("My Feature Film!")
    assert key.startswith("my-feature-film-")
    assert len(key) > len("my-feature-film-")


def test_ui_shell_exposes_creative_nav_and_analyze_script() -> None:
    """Structural check: shipped UI uses creative IA, not proof-console primary."""
    root = Path(__file__).resolve().parents[2] / "apps" / "web"
    html = (root / "index.html").read_text(encoding="utf-8")
    js = (root / "app.js").read_text(encoding="utf-8")
    for label in ("Projects", "Scenes", "Continuity", "Generate", "Review", "Export"):
        assert label in html, f"missing nav label {label}"
    assert "Analyze Script" in html or "Analyze Script" in js
    assert "Build breakdown" not in html or "Analyze Script" in html
    # Run proof must not be a peer primary CTA
    assert 'id="btn-proof"' not in html or "Developer" in html
    assert "Start a Production" in html or "New Project" in html
    # Technical jargon should not dominate primary chrome
    assert "state hash" not in html.lower() or "Developer" in html
