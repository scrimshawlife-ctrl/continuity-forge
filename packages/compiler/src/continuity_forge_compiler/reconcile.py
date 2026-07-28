"""Deterministic prior-IR identity reconciliation for revision compiles."""

from __future__ import annotations

from uuid import UUID

from continuity_forge_ir import NarrativeAtom, SceneNode, ScriptDocument, SourceSegment


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _atom_key(atom: NarrativeAtom) -> tuple[str, str]:
    return (atom.type.value, _normalized(atom.text))


def _scene_fingerprint(scene: SceneNode) -> tuple[str, tuple[tuple[str, str], ...]]:
    return (
        _normalized(scene.slugline),
        tuple(_atom_key(atom) for atom in scene.atoms),
    )


def _match_atoms(
    current: list[NarrativeAtom],
    prior: list[NarrativeAtom],
) -> dict[UUID, UUID]:
    """Map current atom_id -> prior atom_id for content-stable atoms."""
    mapping: dict[UUID, UUID] = {}
    remaining: dict[tuple[str, str], list[NarrativeAtom]] = {}
    for atom in prior:
        remaining.setdefault(_atom_key(atom), []).append(atom)

    for atom in current:
        key = _atom_key(atom)
        candidates = remaining.get(key)
        if not candidates:
            continue
        matched = candidates.pop(0)
        mapping[atom.atom_id] = matched.atom_id
    return mapping


def _match_scenes(
    current: list[SceneNode],
    prior: list[SceneNode],
) -> tuple[dict[UUID, UUID], dict[UUID, UUID]]:
    """Return (scene_id map, atom_id map) from current provisional IDs to prior IDs."""
    scene_map: dict[UUID, UUID] = {}
    atom_map: dict[UUID, UUID] = {}
    unused = list(prior)

    # Exact structural fingerprint matches first (handles duplicate sluglines).
    for scene in current:
        fingerprint = _scene_fingerprint(scene)
        for index, candidate in enumerate(unused):
            if _scene_fingerprint(candidate) != fingerprint:
                continue
            scene_map[scene.scene_id] = candidate.scene_id
            atom_map.update(_match_atoms(scene.atoms, candidate.atoms))
            unused.pop(index)
            break

    # Remaining scenes: match by slugline in document order among leftovers.
    for scene in current:
        if scene.scene_id in scene_map:
            continue
        slug = _normalized(scene.slugline)
        for index, candidate in enumerate(unused):
            if _normalized(candidate.slugline) != slug:
                continue
            scene_map[scene.scene_id] = candidate.scene_id
            atom_map.update(_match_atoms(scene.atoms, candidate.atoms))
            unused.pop(index)
            break

    return scene_map, atom_map


def reconcile_with_prior(document: ScriptDocument, prior: ScriptDocument) -> ScriptDocument:
    """Reuse stable scene/atom IDs from a prior compile of the same logical script.

    Occurrence-indexed provisional IDs remain the fallback for unmatched content.
    Reconciliation is a pure remapping: source spans, text, and diagnostics are unchanged.
    """
    if document.script_id != prior.script_id:
        return document

    scene_map, atom_map = _match_scenes(document.scenes, prior.scenes)
    atom_map = {**_match_atoms(document.preamble, prior.preamble), **atom_map}

    if not scene_map and not atom_map:
        return document

    def remap_atom(atom: NarrativeAtom, *, parent_scene_id: UUID | None) -> NarrativeAtom:
        new_scene_id = parent_scene_id if parent_scene_id is not None else atom.scene_id
        if atom.scene_id is not None and atom.scene_id in scene_map:
            new_scene_id = scene_map[atom.scene_id]
        return atom.model_copy(
            update={
                "atom_id": atom_map.get(atom.atom_id, atom.atom_id),
                "scene_id": new_scene_id,
            }
        )

    scenes = [
        SceneNode(
            scene_id=scene_map.get(scene.scene_id, scene.scene_id),
            ordinal=scene.ordinal,
            slugline=scene.slugline,
            atoms=[
                remap_atom(
                    atom,
                    parent_scene_id=scene_map.get(scene.scene_id, scene.scene_id),
                )
                for atom in scene.atoms
            ],
        )
        for scene in document.scenes
    ]
    preamble = [remap_atom(atom, parent_scene_id=None) for atom in document.preamble]
    segments = [
        SourceSegment(
            kind=segment.kind,
            source_span=segment.source_span,
            atom_id=(
                atom_map.get(segment.atom_id, segment.atom_id)
                if segment.atom_id is not None
                else None
            ),
        )
        for segment in document.source_segments
    ]

    return document.model_copy(
        update={
            "preamble": preamble,
            "scenes": scenes,
            "source_segments": segments,
        }
    )
