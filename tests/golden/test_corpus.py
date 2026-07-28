from pathlib import Path

import pytest
from continuity_forge_compiler import compile_file
from continuity_forge_ir import NarrativeAtom, ScriptDocument

FIXTURES = Path(__file__).parent / "fixtures"

SUPPORTED_FOUNTAIN = [
    "minimal.fountain",
    "advanced.fountain",
    "continuity.fountain",
    "dialogue_heavy.fountain",
    "flashback.fountain",
    "ambiguous.fountain",
    "duplicate_scenes.fountain",
    "unicode.fountain",
]

SUPPORTED_FDX = [
    "minimal.fdx",
    "advanced.fdx",
]

MALFORMED = [
    "malformed.fountain",
    "malformed.fdx",
]


def _all_atoms(document: ScriptDocument) -> list[NarrativeAtom]:
    return [*document.preamble, *(atom for scene in document.scenes for atom in scene.atoms)]


def _assert_m0_provenance(document: ScriptDocument) -> None:
    assert document.coverage.ratio == 1.0
    assert document.coverage.uncovered_spans == []
    assert document.coverage.source_characters == document.source_length
    assert document.coverage.accounted_characters == document.source_length
    if document.source_length:
        assert document.source_segments
        assert document.source_segments[0].source_span.start_offset == 0
        assert document.source_segments[-1].source_span.end_offset == document.source_length

    cursor = 0
    for segment in document.source_segments:
        assert segment.source_span.start_offset == cursor
        assert segment.source_span.end_offset >= cursor
        cursor = segment.source_span.end_offset
    assert cursor == document.source_length

    for atom in _all_atoms(document):
        span = atom.source_span
        assert 0 <= span.start_offset <= span.end_offset <= document.source_length
        assert span.line_start >= 1
        assert span.line_end >= span.line_start


def _assert_deterministic(path: Path) -> ScriptDocument:
    first = compile_file(path)
    second = compile_file(path)
    assert first == second
    assert first.script_id == second.script_id
    assert [scene.scene_id for scene in first.scenes] == [scene.scene_id for scene in second.scenes]
    return first


@pytest.mark.parametrize(
    "path",
    sorted(FIXTURES.glob("*.fountain")) + sorted(FIXTURES.glob("*.fdx")),
    ids=lambda path: path.name,
)
def test_golden_corpus_has_complete_source_accounting(path: Path) -> None:
    document = compile_file(path)
    _assert_m0_provenance(document)


@pytest.mark.parametrize("name", SUPPORTED_FOUNTAIN + SUPPORTED_FDX)
def test_supported_golden_scripts_compile_without_errors(name: str) -> None:
    document = _assert_deterministic(FIXTURES / name)
    assert not [diagnostic for diagnostic in document.diagnostics if diagnostic.severity == "error"]
    assert document.scenes
    _assert_m0_provenance(document)


@pytest.mark.parametrize("name", MALFORMED)
def test_malformed_golden_scripts_report_errors(name: str) -> None:
    document = compile_file(FIXTURES / name)
    errors = [item for item in document.diagnostics if item.severity == "error"]
    assert errors
    _assert_m0_provenance(document)


def test_continuity_fixture_preserves_props_wardrobe_injury_and_payoff() -> None:
    document = compile_file(FIXTURES / "continuity.fountain")
    text = " ".join(atom.text for atom in _all_atoms(document)).casefold()
    for token in (
        "red keycard",
        "brass compass",
        "jacket",
        "forearm",
        "plant",
        "payoff",
        "enters",
        "exits",
        "flashback",
    ):
        assert token in text
    assert len(document.scenes) >= 3


def test_dialogue_heavy_fixture_keeps_cues_and_extensions() -> None:
    document = compile_file(FIXTURES / "dialogue_heavy.fountain")
    types = [atom.type.value for scene in document.scenes for atom in scene.atoms]
    assert types.count("character") >= 4
    assert types.count("dialogue") >= 5
    assert types.count("parenthetical") >= 2
    cues = {
        atom.text
        for scene in document.scenes
        for atom in scene.atoms
        if atom.type.value == "character"
    }
    assert "MARA (V.O.)" in cues or any("MARA" in cue for cue in cues)
    assert any("Dr. Vale" in cue or "DR. VALE" in cue.upper() for cue in cues)


def test_flashback_fixture_retains_time_shift_headings() -> None:
    document = compile_file(FIXTURES / "flashback.fountain")
    sluglines = " | ".join(scene.slugline for scene in document.scenes).casefold()
    assert "flashback" in sluglines
    assert "present" in sluglines
    assert any(atom.type.value == "transition" for atom in _all_atoms(document))


def test_ambiguous_fixture_does_not_promote_long_uppercase_action_to_character() -> None:
    document = compile_file(FIXTURES / "ambiguous.fountain")
    atoms = document.scenes[0].atoms
    assert atoms[1].type.value == "action"
    assert "too many words" in atoms[1].text.casefold()
    assert any(atom.type.value == "note" for atom in _all_atoms(document))


def test_duplicate_slugline_fixture_assigns_distinct_scene_ids() -> None:
    document = compile_file(FIXTURES / "duplicate_scenes.fountain")
    room_scenes = [scene for scene in document.scenes if scene.slugline == "INT. ROOM - DAY"]
    assert len(room_scenes) == 2
    assert room_scenes[0].scene_id != room_scenes[1].scene_id


def test_advanced_fdx_fixture_covers_flashback_and_payoff() -> None:
    document = compile_file(FIXTURES / "advanced.fdx")
    assert document.format == "fdx"
    assert len(document.scenes) == 3
    blob = " ".join(atom.text for atom in _all_atoms(document)).casefold()
    assert "keycard" in blob
    assert "injury" in blob or "torn" in blob
    assert "payoff" in blob


def test_unicode_fixture_preserves_non_ascii_provenance() -> None:
    path = FIXTURES / "unicode.fountain"
    source = path.read_text(encoding="utf-8")
    document = compile_file(path)
    blob = " ".join(atom.text for atom in _all_atoms(document))
    assert "clé rouge" in blob
    assert "Ça ne doit plus dériver" in blob
    assert "Проверяем хеш" in blob
    assert "確認ハッシュ" in blob
    assert document.source_length == len(source)
    assert document.coverage.accounted_characters == len(source)


def test_continuity_fixture_builds_complete_ledger() -> None:
    from continuity_forge_ledger import EntityKind, FactKind, build_continuity_ledger

    document = compile_file(FIXTURES / "continuity.fountain")
    ledger = build_continuity_ledger(document)
    assert ledger.script_id == document.script_id
    assert len(ledger.scene_contracts) == len(document.scenes)
    assert any(entity.kind == EntityKind.PROP for entity in ledger.entities)
    assert any(fact.kind == FactKind.ENTERS for fact in ledger.facts)
    assert ledger.setup_payoff_links
    assert all(fact.atom_ids for fact in ledger.facts)
