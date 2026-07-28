from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from continuity_forge_ir import (
    AtomType,
    CompileDiagnostic,
    CoverageReport,
    DiagnosticSeverity,
    NarrativeAtom,
    SceneNode,
    ScriptDocument,
    SegmentKind,
    SourceSegment,
    SourceSpan,
    content_hash,
    stable_id,
)

SCENE_RE = re.compile(r"^(?:INT\.|EXT\.|EST\.|INT/EXT\.|INT\./EXT\.|I/E\.)\s*.+", re.IGNORECASE)
CHARACTER_RE = re.compile(r"^[A-Z][A-Z0-9 _'\-]*(?:\s*\([^)]*\))?\^?$", re.ASCII)
TITLE_PAGE_RE = re.compile(r"^[A-Za-z][A-Za-z ]{0,30}:\s*.*$")
TRANSITIONS = {"CUT TO:", "FADE OUT.", "FADE IN:", "SMASH CUT TO:", "DISSOLVE TO:"}


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _is_character_cue(value: str) -> bool:
    if value.startswith("@"):
        return bool(value[1:].strip())
    return bool(CHARACTER_RE.fullmatch(value)) and len(value.split()) <= 6


def _classify_non_dialogue(value: str, *, title_page: bool) -> tuple[AtomType, str]:
    if title_page and TITLE_PAGE_RE.match(value):
        return AtomType.TITLE_PAGE, value
    if value.startswith(".") and not value.startswith(".."):
        return AtomType.SCENE_HEADING, value[1:].strip()
    if SCENE_RE.match(value):
        return AtomType.SCENE_HEADING, value
    if value == "===" or (value.startswith("===") and set(value) == {"="}):
        return AtomType.PAGE_BREAK, value
    if value.startswith("#"):
        return AtomType.SECTION, value.lstrip("#").strip()
    if value.startswith("="):
        return AtomType.SYNOPSIS, value[1:].strip()
    if value.startswith("[[") and value.endswith("]]"):
        return AtomType.NOTE, value[2:-2].strip()
    if value.startswith(">") and value.endswith("<"):
        return AtomType.CENTERED, value[1:-1].strip()
    if value.startswith("~"):
        return AtomType.LYRICS, value[1:].strip()
    if value.startswith(">"):
        return AtomType.TRANSITION, value[1:].strip()
    if value.upper() in TRANSITIONS or value.endswith(" TO:") and value == value.upper():
        return AtomType.TRANSITION, value
    return AtomType.ACTION, value[1:].strip() if value.startswith("!") else value


def _script_identity(*, document_key: str | None, source_hash: str) -> str:
    """Prefer an explicit document key; otherwise key identity to source content."""
    if document_key is not None:
        return _normalized(document_key)
    return source_hash


def _split_line_boneyards(
    raw_line: str,
    *,
    line_start: int,
    line_no: int,
    in_boneyard: bool,
) -> tuple[list[tuple[str, SourceSpan]], bool]:
    """Partition a line into comment/live spans and report trailing boneyard state."""
    parts: list[tuple[str, SourceSpan]] = []
    index = 0
    length = len(raw_line)

    def span_for(start: int, end: int) -> SourceSpan:
        return SourceSpan(
            start_offset=line_start + start,
            end_offset=line_start + end,
            line_start=line_no,
            line_end=line_no,
        )

    while index < length:
        if in_boneyard:
            closer = raw_line.find("*/", index)
            if closer == -1:
                parts.append(("comment", span_for(index, length)))
                return parts, True
            end = closer + 2
            parts.append(("comment", span_for(index, end)))
            in_boneyard = False
            index = end
            continue

        opener = raw_line.find("/*", index)
        if opener == -1:
            parts.append(("live", span_for(index, length)))
            return parts, False
        if opener > index:
            parts.append(("live", span_for(index, opener)))
        in_boneyard = True
        index = opener

    return parts, in_boneyard


def compile_text(
    text: str,
    *,
    title: str = "Untitled",
    revision: str = "0.1.0",
    document_key: str | None = None,
) -> ScriptDocument:
    """Compile Fountain source into deterministic, provenance-complete Production IR."""
    source_hash = content_hash(text)
    script_id = stable_id(
        "script", _script_identity(document_key=document_key, source_hash=source_hash)
    )
    lines = text.splitlines(keepends=True)
    if text and (not lines or sum(map(len, lines)) != len(text)):
        lines = text.splitlines(keepends=True)

    scenes: list[SceneNode] = []
    preamble: list[NarrativeAtom] = []
    segments: list[SourceSegment] = []
    diagnostics: list[CompileDiagnostic] = []
    current_scene_id: UUID | None = None
    current_slugline: str | None = None
    current_atoms: list[NarrativeAtom] = []
    scene_occurrences: defaultdict[str, int] = defaultdict(int)
    atom_occurrences: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    offset = 0
    dialogue_active = False
    title_page_active = True
    in_boneyard = False

    def flush_scene() -> None:
        nonlocal current_atoms, current_scene_id, current_slugline
        if current_scene_id is None or current_slugline is None:
            return
        scenes.append(
            SceneNode(
                scene_id=current_scene_id,
                ordinal=len(scenes) + 1,
                slugline=current_slugline,
                atoms=current_atoms,
            )
        )
        current_atoms = []

    def add_atom(atom_type: AtomType, value: str, span: SourceSpan) -> NarrativeAtom:
        scope = str(current_scene_id or script_id)
        occurrence_key = (scope, atom_type.value, _normalized(value))
        atom_occurrences[occurrence_key] += 1
        atom_id = stable_id("atom", *occurrence_key, atom_occurrences[occurrence_key])
        atom = NarrativeAtom(
            atom_id=atom_id,
            scene_id=current_scene_id,
            type=atom_type,
            text=value,
            source_span=span,
            required_on_screen=atom_type
            not in {
                AtomType.TITLE_PAGE,
                AtomType.CHARACTER,
                AtomType.SECTION,
                AtomType.SYNOPSIS,
                AtomType.NOTE,
                AtomType.PAGE_BREAK,
            },
        )
        (current_atoms if current_scene_id else preamble).append(atom)
        segments.append(SourceSegment(kind=SegmentKind.ELEMENT, source_span=span, atom_id=atom_id))
        return atom

    def process_live(raw_fragment: str, span: SourceSpan) -> None:
        nonlocal dialogue_active, title_page_active, current_scene_id, current_slugline
        value = raw_fragment.strip()
        if not value:
            segments.append(SourceSegment(kind=SegmentKind.BLANK, source_span=span))
            dialogue_active = False
            title_page_active = False
            return

        atom_type, parsed_value = _classify_non_dialogue(value, title_page=title_page_active)
        if atom_type == AtomType.SCENE_HEADING:
            flush_scene()
            normalized_slugline = _normalized(parsed_value)
            scene_occurrences[normalized_slugline] += 1
            current_scene_id = stable_id(
                "scene", script_id, normalized_slugline, scene_occurrences[normalized_slugline]
            )
            current_slugline = parsed_value
            dialogue_active = False
            add_atom(atom_type, parsed_value, span)
            return

        if dialogue_active:
            if value.startswith("(") and value.endswith(")"):
                add_atom(AtomType.PARENTHETICAL, value, span)
            else:
                add_atom(AtomType.DIALOGUE, value, span)
            return

        if _is_character_cue(value) and current_scene_id is not None:
            cue = value[1:].strip() if value.startswith("@") else value.removesuffix("^").strip()
            add_atom(AtomType.CHARACTER, cue, span)
            dialogue_active = True
            return

        add_atom(atom_type, parsed_value, span)
        if current_scene_id is None and atom_type != AtomType.TITLE_PAGE:
            diagnostics.append(
                CompileDiagnostic(
                    code="CF101",
                    severity=DiagnosticSeverity.WARNING,
                    message="Content before the first scene heading was retained in the preamble.",
                    source_span=span,
                )
            )

    for line_no, raw_line in enumerate(lines, start=1):
        line_start = offset
        line_end = offset + len(raw_line)
        offset = line_end
        parts, in_boneyard = _split_line_boneyards(
            raw_line,
            line_start=line_start,
            line_no=line_no,
            in_boneyard=in_boneyard,
        )
        for kind, span in parts:
            if kind == "comment":
                segments.append(SourceSegment(kind=SegmentKind.COMMENT, source_span=span))
                dialogue_active = False
                continue
            fragment = text[span.start_offset : span.end_offset]
            process_live(fragment, span)

    flush_scene()
    if in_boneyard:
        diagnostics.append(
            CompileDiagnostic(
                code="CF102",
                severity=DiagnosticSeverity.ERROR,
                message="Unclosed boneyard comment.",
                source_span=segments[-1].source_span if segments else None,
            )
        )
    if not scenes:
        diagnostics.append(
            CompileDiagnostic(
                code="CF100",
                severity=DiagnosticSeverity.ERROR,
                message="No scene headings were found.",
            )
        )

    element_characters = sum(
        segment.source_span.end_offset - segment.source_span.start_offset
        for segment in segments
        if segment.kind == SegmentKind.ELEMENT
    )
    trivia_characters = len(text) - element_characters
    coverage = CoverageReport(
        source_characters=len(text),
        accounted_characters=len(text),
        element_characters=element_characters,
        trivia_characters=trivia_characters,
        ratio=1.0,
        uncovered_spans=[],
    )
    return ScriptDocument(
        script_id=script_id,
        title=title,
        revision=revision,
        source_hash=source_hash,
        source_length=len(text),
        preamble=preamble,
        scenes=scenes,
        source_segments=segments,
        diagnostics=diagnostics,
        coverage=coverage,
    )


def compile_file(path: Path, *, document_key: str | None = None) -> ScriptDocument:
    if path.suffix.casefold() == ".fdx":
        from .fdx import compile_fdx_text

        return compile_fdx_text(
            path.read_text(encoding="utf-8"),
            title=path.stem,
            document_key=document_key or path.stem,
        )
    return compile_text(
        path.read_text(encoding="utf-8"),
        title=path.stem,
        document_key=document_key or path.stem,
    )
