from __future__ import annotations

import re
from collections import defaultdict
from uuid import UUID
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError

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

from .reconcile import reconcile_with_prior

PARAGRAPH_RE = re.compile(r"<Paragraph\b[^>]*>.*?</Paragraph\s*>", re.DOTALL | re.IGNORECASE)
TYPE_RE = re.compile(r'\bType\s*=\s*(["\'])(.*?)\1', re.IGNORECASE)
FDX_TYPES = {
    "scene heading": AtomType.SCENE_HEADING,
    "action": AtomType.ACTION,
    "character": AtomType.CHARACTER,
    "parenthetical": AtomType.PARENTHETICAL,
    "dialogue": AtomType.DIALOGUE,
    "transition": AtomType.TRANSITION,
    "shot": AtomType.ACTION,
    "general": AtomType.ACTION,
}


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _span(source: str, start: int, end: int) -> SourceSpan:
    line_start = source.count("\n", 0, start) + 1
    line_end = line_start + source.count("\n", start, end)
    return SourceSpan(
        start_offset=start,
        end_offset=end,
        line_start=line_start,
        line_end=line_end,
    )


def _paragraph_text(fragment: str) -> str:
    element = ElementTree.fromstring(fragment)
    return "".join(element.itertext()).strip()


def compile_fdx_text(
    text: str,
    *,
    title: str = "Untitled",
    revision: str = "0.1.0",
    document_key: str | None = None,
    prior: ScriptDocument | None = None,
) -> ScriptDocument:
    """Compile Final Draft XML into provenance-complete Production IR."""
    source_hash = content_hash(text)
    identity = _normalized(document_key) if document_key is not None else source_hash
    script_id = stable_id("script", identity)
    diagnostics: list[CompileDiagnostic] = []
    scenes: list[SceneNode] = []
    preamble: list[NarrativeAtom] = []
    segments: list[SourceSegment] = []

    try:
        ElementTree.fromstring(text)
    except ParseError as error:
        if text:
            segments.append(
                SourceSegment(kind=SegmentKind.METADATA, source_span=_span(text, 0, len(text)))
            )
        diagnostics.extend(
            [
                CompileDiagnostic(
                    code="FDX100",
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Malformed Final Draft XML: {error}.",
                ),
                CompileDiagnostic(
                    code="FDX102",
                    severity=DiagnosticSeverity.ERROR,
                    message="No scene headings were found in the FDX document.",
                ),
            ]
        )
        document = _document(
            script_id=script_id,
            title=title,
            revision=revision,
            source_hash=source_hash,
            text=text,
            preamble=preamble,
            scenes=scenes,
            segments=segments,
            diagnostics=diagnostics,
        )
        if prior is not None:
            return reconcile_with_prior(document, prior)
        return document

    current_scene_id = None
    current_slugline: str | None = None
    current_atoms: list[NarrativeAtom] = []
    scene_occurrences: defaultdict[str, int] = defaultdict(int)
    atom_occurrences: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    cursor = 0

    def flush_scene() -> None:
        nonlocal current_atoms
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

    for match in PARAGRAPH_RE.finditer(text):
        if match.start() > cursor:
            segments.append(
                SourceSegment(
                    kind=SegmentKind.METADATA,
                    source_span=_span(text, cursor, match.start()),
                )
            )
        fragment = match.group(0)
        span = _span(text, match.start(), match.end())
        type_match = TYPE_RE.search(fragment)
        fdx_type = type_match.group(2).strip().casefold() if type_match else "general"
        atom_type = FDX_TYPES.get(fdx_type, AtomType.ACTION)
        value = _paragraph_text(fragment)
        if fdx_type not in FDX_TYPES:
            diagnostics.append(
                CompileDiagnostic(
                    code="FDX101",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Unsupported FDX paragraph type '{fdx_type}' was retained as action.",
                    source_span=span,
                )
            )

        if atom_type == AtomType.SCENE_HEADING:
            flush_scene()
            normalized_slugline = _normalized(value)
            scene_occurrences[normalized_slugline] += 1
            current_scene_id = stable_id(
                "scene", script_id, normalized_slugline, scene_occurrences[normalized_slugline]
            )
            current_slugline = value

        scope = str(current_scene_id or script_id)
        occurrence_key = (scope, atom_type.value, _normalized(value))
        atom_occurrences[occurrence_key] += 1
        atom = NarrativeAtom(
            atom_id=stable_id("atom", *occurrence_key, atom_occurrences[occurrence_key]),
            scene_id=current_scene_id,
            type=atom_type,
            text=value,
            source_span=span,
            required_on_screen=atom_type != AtomType.CHARACTER,
        )
        (current_atoms if current_scene_id else preamble).append(atom)
        segments.append(
            SourceSegment(kind=SegmentKind.ELEMENT, source_span=span, atom_id=atom.atom_id)
        )
        if current_scene_id is None:
            diagnostics.append(
                CompileDiagnostic(
                    code="FDX103",
                    severity=DiagnosticSeverity.WARNING,
                    message="FDX content before the first scene was retained in the preamble.",
                    source_span=span,
                )
            )
        cursor = match.end()

    if cursor < len(text):
        segments.append(
            SourceSegment(kind=SegmentKind.METADATA, source_span=_span(text, cursor, len(text)))
        )
    flush_scene()
    if not scenes:
        diagnostics.append(
            CompileDiagnostic(
                code="FDX102",
                severity=DiagnosticSeverity.ERROR,
                message="No scene headings were found in the FDX document.",
            )
        )
    document = _document(
        script_id=script_id,
        title=title,
        revision=revision,
        source_hash=source_hash,
        text=text,
        preamble=preamble,
        scenes=scenes,
        segments=segments,
        diagnostics=diagnostics,
    )
    if prior is not None:
        return reconcile_with_prior(document, prior)
    return document


def _document(
    *,
    script_id: UUID,
    title: str,
    revision: str,
    source_hash: str,
    text: str,
    preamble: list[NarrativeAtom],
    scenes: list[SceneNode],
    segments: list[SourceSegment],
    diagnostics: list[CompileDiagnostic],
) -> ScriptDocument:
    element_characters = sum(
        segment.source_span.end_offset - segment.source_span.start_offset
        for segment in segments
        if segment.kind == SegmentKind.ELEMENT
    )
    return ScriptDocument(
        script_id=script_id,
        title=title,
        format="fdx",
        revision=revision,
        source_hash=source_hash,
        source_length=len(text),
        preamble=preamble,
        scenes=scenes,
        source_segments=segments,
        diagnostics=diagnostics,
        coverage=CoverageReport(
            source_characters=len(text),
            accounted_characters=len(text),
            element_characters=element_characters,
            trivia_characters=len(text) - element_characters,
            ratio=1.0,
        ),
    )
