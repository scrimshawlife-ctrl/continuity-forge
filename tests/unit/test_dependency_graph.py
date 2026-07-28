"""Golden / determinism tests for dependency-graph invalidation (long-form 4.3)."""

from __future__ import annotations

from pathlib import Path

from continuity_forge_compiler import compile_text
from continuity_forge_ir import (
    ArtifactKind,
    ChangeSet,
    artifact_id,
    build_graph,
    compute_stale,
    stale_shot_ids,
)
from continuity_forge_shots import compile_shot_contracts, preview_invalidation

FIXTURE = Path(__file__).parents[1] / "golden" / "fixtures" / "continuity.fountain"


def test_build_graph_edges_are_sorted_and_deterministic() -> None:
    g1 = build_graph(
        source_key="abc",
        scenes=[("s1", ["a1", "a2"]), ("s2", ["a3"])],
        shots=[
            ("sh2", "s2", ["a3"], []),
            ("sh1", "s1", ["a1"], ["e1"]),
        ],
        proposed_by_shot=[("cand1", "sh1")],
    )
    g2 = build_graph(
        source_key="abc",
        scenes=[("s2", ["a3"]), ("s1", ["a2", "a1"])],
        shots=[
            ("sh1", "s1", ["a1"], ["e1"]),
            ("sh2", "s2", ["a3"], []),
        ],
        proposed_by_shot=[("cand1", "sh1")],
    )
    assert g1.nodes == g2.nodes
    assert g1.children == g2.children
    assert artifact_id(ArtifactKind.SOURCE, "abc") in g1.nodes
    assert artifact_id(ArtifactKind.PROPOSED_CANDIDATE, "cand1") in g1.nodes


def test_scene_change_stales_descendant_shots_not_unrelated() -> None:
    g = build_graph(
        source_key="src",
        scenes=[("s1", ["a1"]), ("s2", ["a2"])],
        shots=[
            ("sh1", "s1", ["a1"], []),
            ("sh2", "s2", ["a2"], []),
        ],
    )
    report = compute_stale(g, ChangeSet(scene_ids=["s1"]))
    assert artifact_id(ArtifactKind.SCENE, "s1") in report.stale_ids
    assert artifact_id(ArtifactKind.SHOT_CONTRACT, "sh1") in report.stale_ids
    assert artifact_id(ArtifactKind.SHOT_CONTRACT, "sh2") not in report.stale_ids
    assert stale_shot_ids(report) == ["sh1"]
    assert "never" in report.authority_note.lower() or "PROPOSED" in report.authority_note


def test_source_changed_force_full_stales_all_non_source() -> None:
    g = build_graph(
        source_key="src",
        scenes=[("s1", ["a1"])],
        shots=[("sh1", "s1", ["a1"], [])],
        proposed_by_shot=[("c1", "sh1")],
    )
    report = compute_stale(g, ChangeSet(source_changed=True))
    assert report.force_full is True
    assert artifact_id(ArtifactKind.SOURCE, "src") not in report.stale_ids
    assert artifact_id(ArtifactKind.SHOT_CONTRACT, "sh1") in report.stale_ids
    assert artifact_id(ArtifactKind.PROPOSED_CANDIDATE, "c1") in report.stale_ids


def test_empty_change_yields_empty_stale() -> None:
    g = build_graph(
        source_key="src",
        scenes=[("s1", ["a1"])],
        shots=[("sh1", "s1", ["a1"], [])],
    )
    report = compute_stale(g, ChangeSet())
    assert report.stale_ids == []
    assert report.seed_ids == []


def test_unknown_seed_ids_ignored() -> None:
    g = build_graph(
        source_key="src",
        scenes=[("s1", ["a1"])],
        shots=[("sh1", "s1", ["a1"], [])],
    )
    report = compute_stale(g, ChangeSet(scene_ids=["does-not-exist"]))
    assert report.stale_ids == []


def test_preview_invalidation_on_golden_fixture_is_deterministic() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    doc = compile_text(text, title="Continuity Sample", document_key="cont")
    bundle = compile_shot_contracts(doc)
    assert bundle.contracts

    scene0 = str(bundle.contracts[0].scene_id)
    first = preview_invalidation(doc, bundle, ChangeSet(scene_ids=[scene0]))
    second = preview_invalidation(doc, bundle, ChangeSet(scene_ids=[scene0]))
    assert first.stale_ids == second.stale_ids
    assert first.seed_ids == second.seed_ids
    assert first.model_dump() == second.model_dump()

    shots = stale_shot_ids(first)
    assert shots
    # All stale shots for that scene share the scene seed path
    for contract in bundle.contracts:
        key = str(contract.shot_id)
        if str(contract.scene_id) == scene0:
            assert key in shots
        else:
            assert key not in shots


def test_dependency_graph_module_does_not_import_providers() -> None:
    import ast
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "production_ir"
        / "src"
        / "continuity_forge_ir"
        / "dependency_graph.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "providers" not in alias.name
                assert "persistence" not in alias.name
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "providers" not in node.module
            assert "persistence" not in node.module
