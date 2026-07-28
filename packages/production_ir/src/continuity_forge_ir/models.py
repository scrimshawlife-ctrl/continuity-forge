from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
from typing import Annotated
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, Field


class AtomType(StrEnum):
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    DIALOGUE = "dialogue"
    TRANSITION = "transition"


class CoverageStatus(StrEnum):
    UNPLANNED = "unplanned"
    PLANNED = "planned"
    GENERATED = "generated"
    VALIDATED = "validated"
    WAIVED = "waived"


class SourceSpan(BaseModel):
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    line_start: Annotated[int, Field(ge=1)]
    line_end: Annotated[int, Field(ge=1)]


class NarrativeAtom(BaseModel):
    atom_id: UUID
    scene_id: UUID
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


class ScriptDocument(BaseModel):
    script_id: UUID
    title: str
    format: str
    revision: str
    source_hash: str
    scenes: list[SceneNode]


def content_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def stable_id(namespace: str, *parts: object) -> UUID:
    canonical = "|".join([namespace, *(str(part).strip() for part in parts)])
    return uuid5(NAMESPACE_URL, canonical)
