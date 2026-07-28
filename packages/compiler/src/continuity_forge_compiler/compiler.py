from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import UUID

from continuity_forge_ir import (
    AtomType,
    CompileDiagnostic,
    CompileResult,
    CoverageReport,
    DiagnosticSeverity,
    NarrativeAtom,
    SceneNode,
    ScriptDocument,
    ScriptMetadataEntry,
    SourceSpan,
    content_hash,
    stable_id,
)

SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|I/E\.).+", re.IGNORECASE)
CHARACTER_RE = re.compile(r"^[A-Z][A-Z0-9 ._()'-]{1,48}$")
METADATA_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 _-]{0,48}):\s*(.+)$")
TRANSITIONS = {"CUT TO:", "FADE OUT.", "FADE IN:"}
SUPPORTED_TEXT_SUFFIXES = {".fountain", ".txt"}


def _coverage_report(
    text: str,
    atoms: list[NarrativeAtom],
    additional_spans: list[SourceSpan] | None = None,
) -> CoverageReport:
    covered_character_offsets: set[int] = set()
    for atom in atoms:
        covered_character_offsets.update(
            range(atom.source_span.start_offset, atom.source_span.end_offset)
        )
    for span in additional_spans or []:
        covered_character_offsets.update(range(span.start_offset, span.end_offset))

    non_whitespace_character_offsets = {
        index for index, character in enumerate(text) if not character.isspace()
    }
    uncovered_character_offsets = (
        non_whitespace_character_offsets - covered_character_offsets
    )
    covered_bytes = sum(
        len(character.encode("utf-8"))
        for index, character in enumerate(text)
        if index in covered_character_offsets
    )
    non_whitespace_bytes = sum(
        len(character.encode("utf-8"))
        for index, character in enumerate(text)
        if index in non_whitespace_character_offsets
    )
    uncovered_non_whitespace_bytes = sum(
        len(character.encode("utf-8"))
        for index, character in enumerate(text)
        if index in uncovered_character_offsets
    )
    ratio = (
        1.0
        if non_whitespace_bytes == 0
        else (non_whitespace_bytes - uncovered_non_whitespace_bytes) / non_whitespace_bytes
    )
    return CoverageReport(
        source_bytes=len(text.encode("utf-8")),
        covered_bytes=covered_bytes,
        uncovered_non_whitespace_bytes=uncovered_non_whitespace_bytes,
        emitted_atom_count=len(atoms),
        source_coverage_ratio=ratio,
    )


def _failed_result(
    source: str,
    *,
    title: str,
    revision: str,
    source_format: str,
    code: str,
    message: str,
) -> CompileResult:
    source_hash = content_hash(source)
    document = ScriptDocument(
        script_id=stable_id("script", source_hash),
        title=title,
        format=source_format,
        revision=revision,
        source_hash=source_hash,
        scenes=[],
    )
    return CompileResult(
        document=document,
        diagnostics=[
            CompileDiagnostic(
                code=code,
                severity=DiagnosticSeverity.ERROR,
                message=message,
            )
        ],
        coverage=_coverage_report(source, []),
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
    metadata: list[ScriptMetadataEntry] = []
    diagnostics: list[CompileDiagnostic] = []
    current_slugline: str | None = None
    current_scene_id: UUID | None = None
    current_atoms: list[NarrativeAtom] = []
    all_atoms: list[NarrativeAtom] = []
    offset = 0
    pending_character: tuple[str, SourceSpan] | None = None
    dialogue_parts: list[str] = []
    dialogue_end_offset = 0
    dialogue_end_line = 0
    pending_metadata_index: int | None = None

    def emit_atom(atom_type: AtomType, atom_text: str, span: SourceSpan) -> None:
        if current_scene_id is None:
            raise RuntimeError("cannot emit atom without an active scene")
        atom_id = stable_id(
            "atom", current_scene_id, len(current_atoms) + 1, atom_type, atom_text
        )
        current_atoms.append(
            NarrativeAtom(
                atom_id=atom_id,
                scene_id=current_scene_id,
                type=atom_type,
                text=atom_text,
                source_span=span,
            )
        )

    def flush_dialogue() -> None:
        nonlocal pending_character, dialogue_parts, dialogue_end_offset, dialogue_end_line
        if pending_character is None:
            return
        if not dialogue_parts:
            diagnostics.append(
                CompileDiagnostic(
                    code="CF_PARSE_ORPHAN_CHARACTER",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Character cue '{pending_character[0]}' has no dialogue.",
                    source_span=pending_character[1],
                )
            )
        else:
            span = SourceSpan(
                start_offset=pending_character[1].start_offset,
                end_offset=dialogue_end_offset,
                line_start=pending_character[1].line_start,
                line_end=dialogue_end_line,
            )
            emit_atom(
                AtomType.DIALOGUE,
                f"{pending_character[0]}: " + "\n".join(dialogue_parts),
                span,
            )
        pending_character = None
        dialogue_parts = []
        dialogue_end_offset = 0
        dialogue_end_line = 0

    def flush_scene() -> None:
        nonlocal current_atoms, current_slugline, current_scene_id
        flush_dialogue()
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
            flush_dialogue()
            if current_scene_id is None:
                pending_metadata_index = None
            continue

        if pending_character is not None:
            dialogue_parts.append(stripped)
            dialogue_end_offset = line_end
            dialogue_end_line = line_no
            continue

        if SCENE_RE.match(stripped):
            pending_metadata_index = None
            flush_scene()
            current_slugline = stripped
            current_scene_id = stable_id("scene", script_id, len(scenes) + 1, stripped)
            emit_atom(AtomType.SCENE_HEADING, stripped, span)
        elif current_scene_id is None:
            is_indented = bool(raw_line[:1].isspace())
            if is_indented and pending_metadata_index is not None:
                entry = metadata[pending_metadata_index]
                metadata[pending_metadata_index] = entry.model_copy(
                    update={
                        "value": f"{entry.value}\n{stripped}",
                        "source_span": SourceSpan(
                            start_offset=entry.source_span.start_offset,
                            end_offset=line_end,
                            line_start=entry.source_span.line_start,
                            line_end=line_no,
                        ),
                    }
                )
                continue

            metadata_match = METADATA_RE.match(stripped)
            if metadata_match is not None:
                metadata.append(
                    ScriptMetadataEntry(
                        key=metadata_match.group(1).strip().lower().replace(" ", "_"),
                        value=metadata_match.group(2).strip(),
                        source_span=span,
                    )
                )
                pending_metadata_index = len(metadata) - 1
            else:
                pending_metadata_index = None
                diagnostics.append(
                    CompileDiagnostic(
                        code="CF_PARSE_CONTENT_BEFORE_SCENE",
                        severity=DiagnosticSeverity.WARNING,
                        message="Content before the first scene heading was not emitted.",
                        source_span=span,
                    )
                )
        elif stripped.upper() in TRANSITIONS:
            emit_atom(AtomType.TRANSITION, stripped, span)
        elif CHARACTER_RE.match(stripped) and len(stripped.split()) <= 5:
            pending_character = (stripped, span)
        else:
            emit_atom(AtomType.ACTION, stripped, span)

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
        metadata=metadata,
        scenes=scenes,
    )
    coverage = _coverage_report(
        text,
        all_atoms,
        additional_spans=[entry.source_span for entry in metadata],
    )
    if coverage.uncovered_non_whitespace_bytes:
        diagnostics.append(
            CompileDiagnostic(
                code="CF_COVERAGE_UNEMITTED_SOURCE",
                severity=DiagnosticSeverity.WARNING,
                message=(
                    f"{coverage.uncovered_non_whitespace_bytes} non-whitespace source bytes "
                    "were not represented by emitted atoms or metadata."
                ),
            )
        )
    return CompileResult(document=document, diagnostics=diagnostics, coverage=coverage)


def compile_text(
    text: str, *, title: str = "Untitled", revision: str = "0.1.0"
) -> ScriptDocument:
    return compile_text_result(text, title=title, revision=revision).document


def fdx_to_text(xml_text: str) -> str:
    root = ET.fromstring(xml_text)
    output: list[str] = []
    for paragraph in root.findall(".//Paragraph"):
        paragraph_type = paragraph.attrib.get("Type", "Action")
        paragraph_text = "".join(
            node.text or "" for node in paragraph.findall(".//Text")
        ).strip()
        if not paragraph_text:
            continue
        if paragraph_type == "Scene Heading":
            output.append(paragraph_text)
        elif paragraph_type == "Character":
            output.extend(["", paragraph_text])
        elif paragraph_type in {"Dialogue", "Parenthetical"}:
            output.append(paragraph_text)
        elif paragraph_type == "Transition":
            output.extend(["", paragraph_text])
        else:
            output.extend(["", paragraph_text])
    return "\n".join(output).strip() + "\n"


def compile_fdx_result(
    xml_text: str, *, title: str = "Untitled", revision: str = "0.1.0"
) -> CompileResult:
    try:
        normalized = fdx_to_text(xml_text)
    except ET.ParseError as error:
        return _failed_result(
            xml_text,
            title=title,
            revision=revision,
            source_format="fdx",
            code="CF_FDX_MALFORMED",
            message=f"FDX XML could not be parsed: {error}",
        )
    return compile_text_result(
        normalized,
        title=title,
        revision=revision,
        source_format="fdx",
    )


def compile_file(path: Path) -> ScriptDocument:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".fdx":
        return compile_fdx_result(text, title=path.stem).document
    if suffix in SUPPORTED_TEXT_SUFFIXES:
        return compile_text(text, title=path.stem)
    raise ValueError(f"Unsupported screenplay format: {suffix or '<none>'}")
