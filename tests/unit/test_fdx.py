from pathlib import Path

from continuity_forge_compiler import compile_fdx_text, compile_file
from continuity_forge_ir import AtomType, SegmentKind

FIXTURES = Path(__file__).parents[1] / "golden" / "fixtures"


def test_fdx_paragraphs_compile_to_typed_atoms() -> None:
    document = compile_file(FIXTURES / "minimal.fdx")
    assert document.format == "fdx"
    assert [atom.type for atom in document.scenes[0].atoms] == [
        AtomType.SCENE_HEADING,
        AtomType.ACTION,
        AtomType.CHARACTER,
        AtomType.PARENTHETICAL,
        AtomType.DIALOGUE,
        AtomType.TRANSITION,
    ]
    assert document.coverage.ratio == 1.0
    assert SegmentKind.METADATA in {segment.kind for segment in document.source_segments}


def test_fdx_compile_is_deterministic() -> None:
    source = (FIXTURES / "minimal.fdx").read_text()
    first = compile_fdx_text(source, document_key="fdx-stability")
    second = compile_fdx_text(source, document_key="fdx-stability")
    assert first == second


def test_malformed_fdx_is_accounted_and_diagnosed() -> None:
    source = (FIXTURES / "malformed.fdx").read_text()
    document = compile_fdx_text(source, document_key="malformed-fdx")
    assert {diagnostic.code for diagnostic in document.diagnostics} == {"FDX100", "FDX102"}
    assert document.coverage.ratio == 1.0
    assert document.source_segments[0].source_span.end_offset == len(source)


def test_unknown_fdx_paragraph_type_is_retained_as_action() -> None:
    source = (
        '<FinalDraft><Content><Paragraph Type="Scene Heading"><Text>INT. LAB - DAY</Text>'
        '</Paragraph><Paragraph Type="Custom"><Text>Retained.</Text></Paragraph></Content>'
        "</FinalDraft>"
    )
    document = compile_fdx_text(source, document_key="unknown-fdx")
    assert document.scenes[0].atoms[-1].type == AtomType.ACTION
    assert document.diagnostics[0].code == "FDX101"
