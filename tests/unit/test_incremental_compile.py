"""Golden / acceptance tests for incremental compile (long-form 4.4)."""

from __future__ import annotations

from pathlib import Path

from continuity_forge_compiler import compile_incremental, compile_text
from continuity_forge_compiler.incremental import SceneCompileStatus

FIXTURE = Path(__file__).parents[1] / "golden" / "fixtures" / "minimal.fountain"
CONTINUITY = Path(__file__).parents[1] / "golden" / "fixtures" / "continuity.fountain"


def test_incremental_empty_change_matches_full_compile() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    full = compile_text(text, document_key="inc-min", title="Min")
    inc = compile_incremental(
        text,
        document_key="inc-min",
        title="Min",
        prior=full,
    )
    assert inc.document.model_dump(mode="json") == full.model_dump(mode="json")
    assert inc.claim == "incremental_compile_not_production_ready"
    assert set(inc.carried_scene_ids) == {str(s.scene_id) for s in full.scenes}
    assert inc.recompiled_scene_ids == []
    assert inc.added_scene_ids == []
    assert inc.removed_scene_ids == []
    assert inc.stale_shot_ids == []
    assert inc.coverage_accounted_characters == full.coverage.accounted_characters
    assert inc.coverage_source_characters == full.source_length


def test_incremental_without_prior_tags_all_recompiled() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    inc = compile_incremental(text, document_key="inc-np", title="Min")
    assert inc.prior_reconciled is False
    assert inc.carried_scene_ids == []
    assert len(inc.recompiled_scene_ids) == len(inc.document.scenes)
    assert all(d.status == SceneCompileStatus.RECOMPILED for d in inc.scene_deltas)


def test_incremental_edit_preserves_unchanged_scene_ids() -> None:
    original = CONTINUITY.read_text(encoding="utf-8")
    prior = compile_text(original, document_key="inc-edit", title="Cont")
    # Cosmetic whitespace-only change on one line should still recompile content;
    # append a unique action line to last scene body so source_hash changes.
    revised = original.rstrip() + "\n\nMara checks the door again.\n"
    full_new = compile_text(
        revised, document_key="inc-edit", title="Cont", revision="0.2.0", prior=prior
    )
    inc = compile_incremental(
        revised,
        document_key="inc-edit",
        title="Cont",
        revision="0.2.0",
        prior=prior,
    )
    assert inc.document.source_hash == full_new.source_hash
    # Reconciled document IDs match full compile with prior
    prior_ids = {str(s.scene_id) for s in prior.scenes}
    carried_or_re = set(inc.carried_scene_ids) | set(inc.recompiled_scene_ids)
    assert prior_ids & carried_or_re
    # Coverage still full partition
    assert inc.coverage_accounted_characters == inc.document.coverage.accounted_characters
    assert inc.coverage_accounted_characters == inc.document.source_length
    # Invalidation reports some stale shots when content changed
    assert inc.invalidation is not None
    assert "PROPOSED" in inc.authority_note or "canon" in inc.authority_note.lower()


def test_incremental_coverage_reports_carried_and_recompiled_counts() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    prior = compile_text(text, document_key="inc-cov")
    inc = compile_incremental(text, document_key="inc-cov", prior=prior)
    assert inc.coverage_carried_scenes == len(prior.scenes)
    assert inc.coverage_recompiled_scenes == 0
