from continuity_forge_mcp.server import (
    audit_script_coverage,
    compile_script,
    get_compile_diagnostics,
    get_scene,
    list_scenes,
)

SOURCE = "INT. ROOM - DAY\n\nA lamp flickers.\n"


def test_mcp_compile_and_scene_tools_are_consistent() -> None:
    compiled = compile_script(SOURCE, document_key="mcp-test")
    scenes = list_scenes(SOURCE, document_key="mcp-test")
    assert scenes[0]["scene_id"] == compiled["scenes"][0]["scene_id"]
    assert (
        get_scene(SOURCE, scenes[0]["scene_id"], document_key="mcp-test") == compiled["scenes"][0]
    )


def test_mcp_diagnostics_and_coverage_tools() -> None:
    assert get_compile_diagnostics(SOURCE, document_key="mcp-test") == []
    coverage = audit_script_coverage(SOURCE, document_key="mcp-test")
    assert coverage["ratio"] == 1.0
    assert coverage["uncovered_spans"] == []


def test_mcp_compile_accepts_fdx() -> None:
    source = (
        '<FinalDraft><Content><Paragraph Type="Scene Heading"><Text>INT. LAB - DAY</Text>'
        "</Paragraph></Content></FinalDraft>"
    )
    compiled = compile_script(source, document_key="mcp-fdx", format="fdx")
    assert compiled["format"] == "fdx"
    assert compiled["coverage"]["ratio"] == 1.0


def test_mcp_compile_preserves_revision() -> None:
    compiled = compile_script(SOURCE, document_key="mcp-revision", revision="2.4.0")
    assert compiled["revision"] == "2.4.0"
