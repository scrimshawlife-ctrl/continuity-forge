from pathlib import Path

import pytest
from continuity_forge_compiler import compile_file

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.fountain")), ids=lambda path: path.stem)
def test_golden_corpus_has_complete_source_accounting(path: Path) -> None:
    document = compile_file(path)
    assert document.coverage.ratio == 1.0
    assert document.coverage.uncovered_spans == []
    assert document.source_segments[-1].source_span.end_offset == document.source_length


def test_supported_golden_scripts_compile_without_errors() -> None:
    for name in ["minimal.fountain", "advanced.fountain"]:
        document = compile_file(FIXTURES / name)
        assert not [
            diagnostic for diagnostic in document.diagnostics if diagnostic.severity == "error"
        ]
        assert document.scenes


def test_malformed_golden_script_reports_errors() -> None:
    document = compile_file(FIXTURES / "malformed.fountain")
    assert {diagnostic.code for diagnostic in document.diagnostics} == {"CF100", "CF102"}
