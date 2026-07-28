from pathlib import Path

import pytest

from continuity_forge_compiler import (
    compile_fdx_result,
    compile_file,
    compile_text,
    compile_text_result,
)


def test_compile_is_deterministic() -> None:
    text = "INT. ROOM - DAY\n\nMARA\nHello.\n"
    first = compile_text(text, title="Test")
    second = compile_text(text, title="Test")
    assert first == second
    assert first.source_hash == second.source_hash
    assert len(first.scenes) == 1
    assert len(first.scenes[0].atoms) == 2


def test_source_spans_are_preserved() -> None:
    text = "INT. ROOM - DAY\n\nA lamp flickers.\n"
    document = compile_text(text)
    action = document.scenes[0].atoms[1]
    assert text[action.source_span.start_offset:action.source_span.end_offset].strip() == (
        "A lamp flickers."
    )


def test_compile_result_reports_unemitted_source() -> None:
    result = compile_text_result("TITLE PAGE\n\nINT. ROOM - DAY\n\nA lamp flickers.\n")
    assert result.coverage.uncovered_non_whitespace_bytes > 0
    assert any(
        item.code == "CF_PARSE_CONTENT_BEFORE_SCENE" for item in result.diagnostics
    )
    assert any(
        item.code == "CF_COVERAGE_UNEMITTED_SOURCE" for item in result.diagnostics
    )


def test_orphan_character_is_typed_warning() -> None:
    result = compile_text_result("INT. ROOM - DAY\n\nMARA\n\nThe light dies.\n")
    diagnostic = next(
        item for item in result.diagnostics if item.code == "CF_PARSE_ORPHAN_CHARACTER"
    )
    assert diagnostic.severity == "warning"
    assert diagnostic.source_span is not None


def test_fdx_ingestion_normalizes_to_same_ir_shape() -> None:
    fdx = """<?xml version='1.0' encoding='UTF-8'?>
    <FinalDraft><Content>
      <Paragraph Type='Scene Heading'><Text>INT. ROOM - DAY</Text></Paragraph>
      <Paragraph Type='Action'><Text>A lamp flickers.</Text></Paragraph>
      <Paragraph Type='Character'><Text>MARA</Text></Paragraph>
      <Paragraph Type='Dialogue'><Text>Hello.</Text></Paragraph>
    </Content></FinalDraft>"""
    result = compile_fdx_result(fdx, title="FDX Test")
    assert result.document.format == "fdx"
    assert len(result.document.scenes) == 1
    assert [atom.type for atom in result.document.scenes[0].atoms] == [
        "scene_heading",
        "action",
        "dialogue",
    ]
    assert result.coverage.source_coverage_ratio == 1.0


def test_malformed_fdx_fails_closed_with_typed_error() -> None:
    result = compile_fdx_result("<FinalDraft><Content>")
    assert result.document.scenes == []
    assert any(item.code == "CF_FDX_MALFORMED" for item in result.diagnostics)
    assert any(item.severity == "error" for item in result.diagnostics)


def test_coverage_counts_utf8_bytes() -> None:
    text = "INT. CAFÉ - DAY\n\nA neon sigil glows.\n"
    result = compile_text_result(text)
    assert result.coverage.source_bytes == len(text.encode("utf-8"))


def test_compile_file_rejects_unsupported_format(tmp_path: Path) -> None:
    source = tmp_path / "screenplay.docx"
    source.write_text("not a screenplay", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported screenplay format"):
        compile_file(source)
