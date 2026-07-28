from pathlib import Path

import pytest

from continuity_forge_compiler import compile_fdx_result, compile_text_result
from continuity_forge_ir import AtomType, CompileResult, DiagnosticSeverity

FIXTURES = Path(__file__).parent / "fixtures"
SUPPORTED_FIXTURES = [
    "minimal.fountain",
    "dialogue.fountain",
    "multi_scene.fountain",
    "transitions.fountain",
    "unicode.fountain",
    "minimal.fdx",
]


def compile_fixture(path: Path) -> CompileResult:
    source = path.read_text(encoding="utf-8")
    if path.suffix == ".fdx":
        return compile_fdx_result(source, title=path.stem)
    return compile_text_result(source, title=path.stem)


@pytest.mark.parametrize("fixture_name", SUPPORTED_FIXTURES)
def test_supported_golden_fixture_is_deterministic(fixture_name: str) -> None:
    path = FIXTURES / fixture_name
    first = compile_fixture(path)
    second = compile_fixture(path)

    assert first.model_dump_json() == second.model_dump_json()
    assert first.document.source_hash == second.document.source_hash
    assert first.document.script_id == second.document.script_id


@pytest.mark.parametrize("fixture_name", SUPPORTED_FIXTURES)
def test_supported_golden_fixture_has_zero_silent_omissions(fixture_name: str) -> None:
    result = compile_fixture(FIXTURES / fixture_name)

    assert result.document.scenes
    assert result.coverage.uncovered_non_whitespace_bytes == 0
    assert result.coverage.source_coverage_ratio == 1.0
    assert not any(
        diagnostic.code == "CF_COVERAGE_UNEMITTED_SOURCE"
        for diagnostic in result.diagnostics
    )
    assert not any(
        diagnostic.severity == DiagnosticSeverity.ERROR
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("fixture_name", SUPPORTED_FIXTURES)
def test_supported_golden_fixture_has_valid_atom_provenance(fixture_name: str) -> None:
    result = compile_fixture(FIXTURES / fixture_name)

    for scene in result.document.scenes:
        assert scene.atoms
        for atom in scene.atoms:
            assert atom.scene_id == scene.scene_id
            assert atom.source_span.start_offset < atom.source_span.end_offset
            assert atom.source_span.line_start <= atom.source_span.line_end


def test_transition_fixture_preserves_transition_and_uppercase_dialogue() -> None:
    result = compile_fixture(FIXTURES / "transitions.fountain")
    atom_types = [
        atom.type
        for scene in result.document.scenes
        for atom in scene.atoms
    ]
    atom_text = [
        atom.text
        for scene in result.document.scenes
        for atom in scene.atoms
    ]

    assert atom_types.count(AtomType.TRANSITION) == 2
    assert "MARA: NO." in atom_text
    assert not any(
        diagnostic.code == "CF_PARSE_ORPHAN_CHARACTER"
        for diagnostic in result.diagnostics
    )
