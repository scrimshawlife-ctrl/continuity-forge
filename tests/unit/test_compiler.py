import pytest
from continuity_forge_compiler import compile_text
from continuity_forge_ir import AtomType, DiagnosticSeverity, ScriptDocument


def test_compile_is_deterministic_and_fully_accounted() -> None:
    text = "INT. ROOM - DAY\n\nMARA\nHello.\n"
    first = compile_text(text, title="Test", document_key="test-script")
    second = compile_text(text, title="Test", document_key="test-script")

    assert first == second
    assert first.coverage.ratio == 1.0
    assert first.coverage.accounted_characters == len(text)
    assert [atom.type for atom in first.scenes[0].atoms] == [
        AtomType.SCENE_HEADING,
        AtomType.CHARACTER,
        AtomType.DIALOGUE,
    ]


def test_source_segments_partition_every_character() -> None:
    text = "Title: Example\n\n/* hidden\nmaterial */\nINT. ROOM - DAY\n\nA lamp flickers.\n"
    document = compile_text(text, document_key="segments")

    cursor = 0
    for segment in document.source_segments:
        assert segment.source_span.start_offset == cursor
        cursor = segment.source_span.end_offset
    assert cursor == len(text)
    assert document.coverage.uncovered_spans == []


def test_uppercase_action_is_not_misclassified_as_character() -> None:
    document = compile_text(
        "INT. LAB - DAY\n\nTHE DOOR EXPLODES.\nSmoke fills the room.\n",
        document_key="uppercase-action",
    )
    atoms = document.scenes[0].atoms
    assert [atom.type for atom in atoms[1:]] == [AtomType.ACTION, AtomType.ACTION]


def test_multiline_dialogue_and_parenthetical_remain_dialogue_block() -> None:
    document = compile_text(
        "INT. LAB - DAY\n\nMARA\n(whispering)\nFirst line.\nSecond line.\n",
        document_key="dialogue",
    )
    assert [atom.type for atom in document.scenes[0].atoms] == [
        AtomType.SCENE_HEADING,
        AtomType.CHARACTER,
        AtomType.PARENTHETICAL,
        AtomType.DIALOGUE,
        AtomType.DIALOGUE,
    ]


def test_fountain_control_elements_are_typed() -> None:
    text = (
        "Title: Example\nAuthor: Writer\n\n# Act One\n= Opening\n[[production note]]\n"
        ".LAB - DAY\n\n> SMASH CUT TO:\n>THE END<\n~Singing\n===\n"
    )
    document = compile_text(text, document_key="controls")
    assert [atom.type for atom in document.preamble] == [
        AtomType.TITLE_PAGE,
        AtomType.TITLE_PAGE,
        AtomType.SECTION,
        AtomType.SYNOPSIS,
        AtomType.NOTE,
    ]
    assert [atom.type for atom in document.scenes[0].atoms] == [
        AtomType.SCENE_HEADING,
        AtomType.TRANSITION,
        AtomType.CENTERED,
        AtomType.LYRICS,
        AtomType.PAGE_BREAK,
    ]


def test_pre_scene_content_is_retained_with_diagnostic() -> None:
    document = compile_text("Preface.\n\nINT. ROOM - DAY\n", document_key="preamble")
    assert document.preamble[0].text == "Preface."
    assert document.diagnostics[0].code == "CF101"


def test_missing_scene_and_unclosed_comment_are_diagnosed() -> None:
    document = compile_text("/* unfinished\n", document_key="bad")
    assert {item.code for item in document.diagnostics} == {"CF100", "CF102"}
    assert all(item.severity == DiagnosticSeverity.ERROR for item in document.diagnostics)


def test_scene_ids_survive_unrelated_scene_insertion() -> None:
    original = compile_text(
        "INT. A - DAY\n\nAction.\n\nEXT. B - NIGHT\n\nMore.\n",
        document_key="revision-stability",
    )
    revised = compile_text(
        "INT. X - DAY\n\nNew.\n\nINT. A - DAY\n\nAction.\n\nEXT. B - NIGHT\n\nMore.\n",
        document_key="revision-stability",
        revision="0.2.0",
    )
    original_ids = {scene.slugline: scene.scene_id for scene in original.scenes}
    revised_ids = {scene.slugline: scene.scene_id for scene in revised.scenes}
    assert revised_ids["INT. A - DAY"] == original_ids["INT. A - DAY"]
    assert revised_ids["EXT. B - NIGHT"] == original_ids["EXT. B - NIGHT"]


def test_atom_ids_survive_unrelated_atom_insertion() -> None:
    original = compile_text("INT. A - DAY\n\nOne.\nTwo.\n", document_key="atom-stability")
    revised = compile_text("INT. A - DAY\n\nZero.\nOne.\nTwo.\n", document_key="atom-stability")
    old = {atom.text: atom.atom_id for atom in original.scenes[0].atoms}
    new = {atom.text: atom.atom_id for atom in revised.scenes[0].atoms}
    assert new["One."] == old["One."]
    assert new["Two."] == old["Two."]


def test_document_schema_rejects_non_contiguous_segments() -> None:
    document = compile_text("INT. A - DAY\n", document_key="invalid")
    payload = document.model_dump()
    payload["source_segments"][0]["source_span"]["start_offset"] = 1
    with pytest.raises(ValueError, match="contiguous partition"):
        ScriptDocument.model_validate(payload)


def test_untitled_sources_without_document_key_do_not_share_script_ids() -> None:
    first = compile_text("INT. ROOM - DAY\n\nOne.\n")
    second = compile_text("INT. ROOM - DAY\n\nTwo.\n")
    assert first.title == second.title == "Untitled"
    assert first.script_id != second.script_id
    assert first.scenes[0].scene_id != second.scenes[0].scene_id


def test_document_key_keeps_script_identity_across_content_revisions() -> None:
    first = compile_text("INT. ROOM - DAY\n\nOne.\n", document_key="stable-doc")
    second = compile_text("INT. ROOM - DAY\n\nTwo.\n", document_key="stable-doc")
    assert first.script_id == second.script_id


def test_live_text_after_inline_boneyard_is_compiled() -> None:
    document = compile_text(
        "/* note */ INT. ROOM - DAY\n\nA lamp flickers.\n",
        document_key="inline-boneyard",
    )
    assert document.scenes[0].slugline == "INT. ROOM - DAY"
    assert document.scenes[0].atoms[1].text == "A lamp flickers."
    assert document.coverage.ratio == 1.0
    assert any(segment.kind.value == "comment" for segment in document.source_segments)


def test_live_text_after_multiline_boneyard_terminator_is_compiled() -> None:
    document = compile_text(
        "/* start\nend */ Action after comment.\n\nINT. ROOM - DAY\n",
        document_key="multiline-boneyard",
    )
    assert document.preamble[0].type == AtomType.ACTION
    assert document.preamble[0].text == "Action after comment."
    assert document.scenes[0].slugline == "INT. ROOM - DAY"
    assert document.diagnostics[0].code == "CF101"


def test_document_schema_rejects_coverage_totals_that_ignore_segments() -> None:
    document = compile_text("INT. A - DAY\n", document_key="coverage-mismatch")
    payload = document.model_dump()
    payload["coverage"]["accounted_characters"] = 0
    payload["coverage"]["element_characters"] = 0
    payload["coverage"]["trivia_characters"] = 0
    payload["coverage"]["ratio"] = 0.0
    with pytest.raises(ValueError, match="coverage accounted characters"):
        ScriptDocument.model_validate(payload)
