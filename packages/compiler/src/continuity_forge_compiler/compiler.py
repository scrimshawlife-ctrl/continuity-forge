from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from continuity_forge_ir import (
    AtomType,
    CompileDiagnostic,
    CompileResult,
    CoverageReport,
    DiagnosticSeverity,
    NarrativeAtom,
    SceneNode,
    ScriptDocument,
    SourceSpan,
    content_hash,
    stable_id,
)

SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|I/E\.).+", re.IGNORECASE)
CHARACTER_RE = re.compile(r"^[A-Z][A-Z0-9 ._()'-]{1,48}$")


def _coverage_report(text: str, atoms: list[NarrativeAtom]) -> CoverageReport:
    covered: set[int] = set()
    for atom in atoms:
        covered.update(range(atom.source_span.start_offset, atom.source_span.end_offset))
    non_whitespace = {index for index, char in enumerate(text) if not char.isspace()}
    uncovered = non_whitespace - covered
    total = len(text)
    ratio = 1.0 if not non_whitespace else (len(non_whitespace) - len(uncovered)) / len(non_whitespace)
    return CoverageReport(
        source_bytes=total,
        covered_bytes=len(covered),
        uncovered_non_whitespace_bytes=len(uncovered),
        emitted_atom_count=len(atoms),
        source_coverage_ratio=ratio,
    )


def compile_text_result(
    text: str,
    *,
    title: str = "Untitled",
    revision: str = "0.1.0",
    source_format: str = "fountain",
) -> CompileResult:
    source_hash = content_hash(text)
    script_id = stable_id("script", source_hash)
    lines = text.splitlines(keepends=True)
    scenes: list[SceneNode] = []
    diagnostics: list[CompileDiagnostic] = []
    current_slugline: str | None = None
    current_scene_id = None
    current_atoms: list[NarrativeAtom] = []
    all_atoms: list[NarrativeAtom] = []
    offset = 0
    pending_character: tuple[str, SourceSpan] | None = None

    def flush_scene() -> None:
        nonlocal current_atoms, current_slugline, current_scene_id
        if current_slugline is None or current_scene_id is None:
            return
        scenes.append(
            SceneNode(
                scene_id=current_scene_id,
                ordinal=len(scenes) + 1,
                slugline=current_slugline,
                atoms=current_atoms,
            )
        )
        all_atoms.extend(current_atoms)
        current_atoms = []

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        line_start = offset
        line_end = offset + len(raw_line)
        offset = line_end
        span = SourceSpan(
            start_offset=line_start,
            end_offset=line_end,
            line_start=line_no,
            line_end=line_no,
        )
        if not stripped:
            if pending_character is not None:
                diagnostics.append(
                    CompileDiagnostic(
                        code="CF_PARSE_ORPHAN_CHARACTER",
                        severity=DiagnosticSeverity.WARNING,
                        message=f"Character cue '{pending_character[0]}' has no dialogue.",
                        source_span=pending_character[1],
                    )
                )
            pending_character = None
            continue

        if SCENE_RE.match(stripped):
            flush_scene()
            current_slugline = stripped
            current_scene_id = stable_id("scene", script_id, len(scenes) + 1, stripped)
            atom_type = AtomType.SCENE_HEADING
        elif current_scene_id is None:
            diagnostics.append(
                CompileDiagnostic(
                    code="CF_PARSE_CONTENT_BEFORE_SCENE",
                    severity=DiagnosticSeverity.WARNING,
                    message="Content before the first scene heading was not emitted.",
                    source_span=span,
                )
            )
            continue
        elif CHARACTER_RE.match(stripped) and len(stripped.split()) <= 5:
            pending_character = (stripped, span)
            continue
        elif pending_character is not None:
            atom_type = AtomType.DIALOGUE
            stripped = f"{pending_character[0]}: {stripped}"
            span = SourceSpan(
                start_offset=pending_character[1].start_offset,
                end_offset=line_end,
                line_start=pending_character[1].line_start,
                line_end=line_no,
            )
            pending_character = None
        elif stripped.upper() in {"CUT TO:", "FADE OUT.", "FADE IN:"}:
            atom_type = AtomType.TRANSITION
        else:
            atom_type = AtomType.ACTION

        assert current_scene_id is not None
        atom_id = stable_id("atom", current_scene_id, len(current_atoms) + 1, atom_type, stripped)
        current_atoms.append(
            NarrativeAtom(
                atom_id=atom_id,
                scene_id=current_scene_id,
                type=atom_type,
                text=stripped,
                source_span=span,
            )
        )

    if pending_character is not None:
        diagnostics.append(
            CompileDiagnostic(
                code="CF_PARSE_ORPHAN_CHARACTER",
                severity=DiagnosticSeverity.WARNING,
                message=f"Character cue '{pending_character[0]}' has no dialogue.",
                source_span=pending_character[1],
            )
        )
    flush_scene()
    if not scenes:
        diagnostics.append(
            CompileDiagnostic(
                code="CF_PARSE_NO_SCENES",
                severity=DiagnosticSeverity.ERROR,
                message="No screenplay scene headings were detected.",
            )
        )

    document = ScriptDocument(
        script_id=script_id,
        title=title,
        format=source_format,
        revision=revision,
        source_hash=source_hash,
        scenes=scenes,
    )
    coverage = _coverage_report(text, all_atoms)
    if coverage.uncovered_non_whitespace_bytes:
        diagnostics.append(
            CompileDiagnostic(
                code="CF_COVERAGE_UNEMITTED_SOURCE",
                severity=DiagnosticSeverity.WARNING,
                message=(
                    f"{coverage.uncovered_non_whitespace_bytes} non-whitespace source bytes "
                    "were not represented by emitted atoms."
                ),
            )
        )
    return CompileResult(document=document, diagnostics=diagnostics, coverage=coverage)


def compile_text(text: str, *, title: str = "Untitled", revision: str = "0.1.0") -> ScriptDocument:
    return compile_text_result(text, title=title, revision=revision).document


def fdx_to_text(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    output: list[str] = []
    for paragraph in root.findall(".//Paragraph"):
        paragraph_type = paragraph.attrib.get("Type", "Action")
        text = "".join(node.text or "" for node in paragraph.findall(".//Text")).strip()
        if not text:
            continue
        if paragraph_type == "Scene Heading":
            output.append(text)
        elif paragraph_type == "Character":
            output.extend(["", text])
        elif paragraph_type == "Dialogue":
            output.append(text)
        elif paragraph_type == "Transition":
            output.extend(["", text])
        else:
            output.extend(["", text])
    return "\n".join(output).strip() + "\n"


def compile_fdx_result(xml_text: str, *, title: str = "Untitled", revision: str = "0.1.0") -> CompileResult:
    normalized = fdx_to_text(xml_text)
    return compile_text_result(
        normalized,
        title=title,
        revision=revision,
        source_format="fdx",
    )


def compile_file(path: Path) -> ScriptDocument:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".fdx":
        return compile_fdx_result(text, title=path.stem).document
    return compile_text(text, title=path.stem)
