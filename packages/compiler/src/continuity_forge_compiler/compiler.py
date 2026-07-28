from __future__ import annotations

import re
from pathlib import Path

from continuity_forge_ir import (
    AtomType,
    NarrativeAtom,
    SceneNode,
    ScriptDocument,
    SourceSpan,
    content_hash,
    stable_id,
)

SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|I/E\.).+", re.IGNORECASE)
CHARACTER_RE = re.compile(r"^[A-Z][A-Z0-9 ._()'-]{1,48}$")


def compile_text(text: str, *, title: str = "Untitled", revision: str = "0.1.0") -> ScriptDocument:
    source_hash = content_hash(text)
    script_id = stable_id("script", source_hash)
    lines = text.splitlines(keepends=True)
    scenes: list[SceneNode] = []
    current_slugline: str | None = None
    current_scene_id = None
    current_atoms: list[NarrativeAtom] = []
    offset = 0
    pending_character: str | None = None

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
        current_atoms = []

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        line_start = offset
        line_end = offset + len(raw_line)
        offset = line_end
        if not stripped:
            pending_character = None
            continue

        if SCENE_RE.match(stripped):
            flush_scene()
            current_slugline = stripped
            current_scene_id = stable_id("scene", script_id, len(scenes) + 1, stripped)
            atom_type = AtomType.SCENE_HEADING
        elif current_scene_id is None:
            continue
        elif CHARACTER_RE.match(stripped) and len(stripped.split()) <= 5:
            pending_character = stripped
            continue
        elif pending_character is not None:
            atom_type = AtomType.DIALOGUE
            stripped = f"{pending_character}: {stripped}"
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
                source_span=SourceSpan(
                    start_offset=line_start,
                    end_offset=line_end,
                    line_start=line_no,
                    line_end=line_no,
                ),
            )
        )

    flush_scene()
    return ScriptDocument(
        script_id=script_id,
        title=title,
        format="screenplay",
        revision=revision,
        source_hash=source_hash,
        scenes=scenes,
    )


def compile_file(path: Path) -> ScriptDocument:
    return compile_text(path.read_text(encoding="utf-8"), title=path.stem)
