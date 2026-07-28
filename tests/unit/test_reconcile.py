from continuity_forge_compiler import compile_text

ORIGINAL = """\
INT. ROOM - DAY

First visit. Lamp is off.

MARA
Clean.

INT. HALL - NIGHT

Bridge.

INT. ROOM - DAY

Second visit. Lamp is on.

MARA
Changed.
"""

# Insert a new duplicate slugline visit before the originals.
REVISED = """\
INT. ROOM - DAY

Zeroth visit. Inserted.

INT. ROOM - DAY

First visit. Lamp is off.

MARA
Clean.

INT. HALL - NIGHT

Bridge.

INT. ROOM - DAY

Second visit. Lamp is on.

MARA
Changed.
"""


def _room_scenes(document):  # type: ignore[no-untyped-def]
    return [scene for scene in document.scenes if scene.slugline == "INT. ROOM - DAY"]


def test_prior_ir_keeps_duplicate_slugline_ids_across_insertion() -> None:
    original = compile_text(ORIGINAL, document_key="dup-revision")
    without_prior = compile_text(REVISED, document_key="dup-revision", revision="0.2.0")
    with_prior = compile_text(
        REVISED,
        document_key="dup-revision",
        revision="0.2.0",
        prior=original,
    )

    original_rooms = _room_scenes(original)
    revised_rooms = _room_scenes(with_prior)
    naive_rooms = _room_scenes(without_prior)

    assert len(original_rooms) == 2
    assert len(revised_rooms) == 3

    # Content-stable scenes keep prior IDs when reconciled.
    by_action = {
        next(atom.text for atom in scene.atoms if atom.type.value == "action"): scene.scene_id
        for scene in revised_rooms
    }
    assert by_action["First visit. Lamp is off."] == original_rooms[0].scene_id
    assert by_action["Second visit. Lamp is on."] == original_rooms[1].scene_id

    # Without prior IR, occurrence fallback renumbers the inserted duplicate.
    assert naive_rooms[1].scene_id != original_rooms[0].scene_id


def test_prior_ir_keeps_atom_ids_for_matched_scenes() -> None:
    original = compile_text(ORIGINAL, document_key="atom-revision")
    revised = compile_text(
        REVISED,
        document_key="atom-revision",
        revision="0.2.0",
        prior=original,
    )

    original_first = _room_scenes(original)[0]
    revised_first = next(
        scene
        for scene in _room_scenes(revised)
        if any(atom.text == "First visit. Lamp is off." for atom in scene.atoms)
    )
    original_atoms = {atom.text: atom.atom_id for atom in original_first.atoms}
    revised_atoms = {atom.text: atom.atom_id for atom in revised_first.atoms}
    assert revised_atoms["First visit. Lamp is off."] == original_atoms["First visit. Lamp is off."]
    assert revised_atoms["Clean."] == original_atoms["Clean."]


def test_prior_from_different_document_key_is_ignored() -> None:
    original = compile_text(ORIGINAL, document_key="doc-a")
    revised = compile_text(
        REVISED,
        document_key="doc-b",
        prior=original,
    )
    # Different script_id means no remapping — occurrence IDs only.
    assert revised.script_id != original.script_id
    assert _room_scenes(revised)[1].scene_id != _room_scenes(original)[0].scene_id


def test_prior_ir_slugline_fallback_when_scene_content_changes() -> None:
    original = compile_text(
        "INT. ROOM - DAY\n\nOld action.\n\nMARA\nHello.\n",
        document_key="content-edit",
    )
    revised = compile_text(
        "INT. ROOM - DAY\n\nNew action after rewrite.\n\nMARA\nHello.\n",
        document_key="content-edit",
        revision="0.2.0",
        prior=original,
    )
    assert revised.scenes[0].scene_id == original.scenes[0].scene_id
    # Unchanged dialogue atom keeps its prior identity; rewritten action does not.
    original_by_text = {atom.text: atom.atom_id for atom in original.scenes[0].atoms}
    revised_by_text = {atom.text: atom.atom_id for atom in revised.scenes[0].atoms}
    assert revised_by_text["Hello."] == original_by_text["Hello."]
    assert "New action after rewrite." in revised_by_text
    assert revised_by_text["New action after rewrite."] != original_by_text["Old action."]
