from continuity_forge_compiler import compile_text


def test_compile_is_deterministic() -> None:
    text = "INT. ROOM - DAY\n\nMARA\nHello.\n"
    first = compile_text(text, title="Test")
    second = compile_text(text, title="Test")
    assert first == second
    assert first.source_hash == second.source_hash
    assert len(first.scenes) == 1
    assert len(first.scenes[0].atoms) == 2


def test_source_spans_are_preserved() -> None:
    text = "INT. ROOM - DAY\n\nA lamp flickers.\n"
    document = compile_text(text)
    action = document.scenes[0].atoms[1]
    assert text[action.source_span.start_offset:action.source_span.end_offset].strip() == "A lamp flickers."
