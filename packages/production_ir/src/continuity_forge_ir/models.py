from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
from typing import Annotated
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field, model_validator


class AtomType(StrEnum):
    TITLE_PAGE = "title_page"
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"
    TRANSITION = "transition"
    SECTION = "section"
    SYNOPSIS = "synopsis"
    NOTE = "note"
    CENTERED = "centered"
    LYRICS = "lyrics"
    PAGE_BREAK = "page_break"


class CoverageStatus(StrEnum):
    UNPLANNED = "unplanned"
    PLANNED = "planned"
    GENERATED = "generated"
    VALIDATED = "validated"
    WAIVED = "waived"


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SegmentKind(StrEnum):
    ELEMENT = "element"
    BLANK = "blank"
    COMMENT = "comment"
    METADATA = "metadata"


class SourceSpan(BaseModel):
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    line_start: Annotated[int, Field(ge=1)]
    line_end: Annotated[int, Field(ge=1)]

    @model_validator(mode="after")
    def validate_order(self) -> SourceSpan:
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset must be greater than or equal to start_offset")
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class CompileDiagnostic(BaseModel):
    code: str
    severity: DiagnosticSeverity
    message: str
    source_span: SourceSpan | None = None


class SourceSegment(BaseModel):
    kind: SegmentKind
    source_span: SourceSpan
    atom_id: UUID | None = None

    @model_validator(mode="after")
    def validate_atom_reference(self) -> SourceSegment:
        if self.kind == SegmentKind.ELEMENT and self.atom_id is None:
            raise ValueError("element segments require atom_id")
        if self.kind != SegmentKind.ELEMENT and self.atom_id is not None:
            raise ValueError("only element segments may reference an atom")
        return self


class CoverageReport(BaseModel):
    source_characters: Annotated[int, Field(ge=0)]
    accounted_characters: Annotated[int, Field(ge=0)]
    element_characters: Annotated[int, Field(ge=0)]
    trivia_characters: Annotated[int, Field(ge=0)]
    ratio: Annotated[float, Field(ge=0, le=1)]
    uncovered_spans: list[SourceSpan] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_totals(self) -> CoverageReport:
        if self.accounted_characters > self.source_characters:
            raise ValueError("accounted characters cannot exceed source characters")
        if self.element_characters + self.trivia_characters != self.accounted_characters:
            raise ValueError("element and trivia totals must equal accounted characters")
        expected = (
            1.0
            if self.source_characters == 0
            else self.accounted_characters / self.source_characters
        )
        if abs(self.ratio - expected) > 1e-12:
            raise ValueError("coverage ratio does not match character totals")
        return self


class NarrativeAtom(BaseModel):
    atom_id: UUID
    scene_id: UUID | None
    type: AtomType
    text: str
    source_span: SourceSpan
    required_on_screen: bool = True
    coverage_status: CoverageStatus = CoverageStatus.UNPLANNED


class SceneNode(BaseModel):
    scene_id: UUID
    ordinal: Annotated[int, Field(ge=1)]
    slugline: str
    atoms: list[NarrativeAtom]

    @model_validator(mode="after")
    def validate_atoms(self) -> SceneNode:
        if not self.atoms:
            raise ValueError("scenes require at least a scene-heading atom")
        if self.atoms[0].type != AtomType.SCENE_HEADING:
            raise ValueError("the first scene atom must be a scene heading")
        if any(atom.scene_id != self.scene_id for atom in self.atoms):
            raise ValueError("every scene atom must reference its parent scene")
        if len({atom.atom_id for atom in self.atoms}) != len(self.atoms):
            raise ValueError("atom IDs must be unique within a scene")
        return self


class ScriptDocument(BaseModel):
    script_id: UUID
    title: str
    format: str = "fountain"
    revision: str
    source_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    source_length: Annotated[int, Field(ge=0)]
    preamble: list[NarrativeAtom] = Field(default_factory=list)
    scenes: list[SceneNode]
    source_segments: list[SourceSegment]
    diagnostics: list[CompileDiagnostic] = Field(default_factory=list)
    coverage: CoverageReport

    @model_validator(mode="after")
    def validate_document(self) -> ScriptDocument:
        if self.format not in {"fountain", "fdx"}:
            raise ValueError("format must be 'fountain' or 'fdx'")
        if [scene.ordinal for scene in self.scenes] != list(range(1, len(self.scenes) + 1)):
            raise ValueError("scene ordinals must be unique and sequential")
        scene_ids = [scene.scene_id for scene in self.scenes]
        if len(set(scene_ids)) != len(scene_ids):
            raise ValueError("scene IDs must be unique")
        if any(atom.scene_id is not None for atom in self.preamble):
            raise ValueError("preamble atoms cannot reference a scene")

        all_atoms = [*self.preamble, *(atom for scene in self.scenes for atom in scene.atoms)]
        atom_ids = {atom.atom_id for atom in all_atoms}
        if len(atom_ids) != len(all_atoms):
            raise ValueError("atom IDs must be unique across the document")
        if any(
            segment.atom_id not in atom_ids for segment in self.source_segments if segment.atom_id
        ):
            raise ValueError("source segments must reference document atoms")

        cursor = 0
        element_characters = 0
        trivia_characters = 0
        for segment in self.source_segments:
            if segment.source_span.start_offset != cursor:
                raise ValueError("source segments must form a contiguous partition")
            width = segment.source_span.end_offset - segment.source_span.start_offset
            cursor = segment.source_span.end_offset
            if segment.kind == SegmentKind.ELEMENT:
                element_characters += width
            else:
                trivia_characters += width
        if cursor != self.source_length:
            raise ValueError("source segments must cover the complete source")
        if self.coverage.source_characters != self.source_length:
            raise ValueError("coverage source length must match the document")
        if self.coverage.accounted_characters != cursor:
            raise ValueError("coverage accounted characters must equal source segment total")
        if self.coverage.element_characters != element_characters:
            raise ValueError("coverage element characters must match element segments")
        if self.coverage.trivia_characters != trivia_characters:
            raise ValueError("coverage trivia characters must match non-element segments")
        return self


def content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def stable_id(namespace: str, *parts: object) -> UUID:
    canonical = "|".join([namespace, *(str(part).strip() for part in parts)])
    return uuid5(NAMESPACE_URL, canonical)
