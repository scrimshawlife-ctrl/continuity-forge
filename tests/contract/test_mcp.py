from uuid import UUID

import pytest

from continuity_forge_mcp import registry

SCRIPT = "INT. ROOM - DAY\n\nA lamp flickers.\n\nMARA\nHello.\n"


def test_registry_exposes_only_read_only_tools() -> None:
    tools = registry.list_tools()
    assert [tool.name for tool in tools] == [
        "cf.audit_script_coverage",
        "cf.get_compile_diagnostics",
        "cf.inspect_scene",
        "cf.list_scenes",
    ]
    assert all(tool.read_only for tool in tools)


def test_list_and_inspect_scene_use_stable_ids() -> None:
    first = registry.call("cf.list_scenes", text=SCRIPT)
    second = registry.call("cf.list_scenes", text=SCRIPT)
    assert first == second
    assert len(first) == 1
    assert isinstance(first[0].scene_id, UUID)

    inspection = registry.call(
        "cf.inspect_scene",
        text=SCRIPT,
        scene_id=first[0].scene_id,
    )
    assert inspection.scene.scene_id == first[0].scene_id
    assert inspection.scene.slugline == "INT. ROOM - DAY"
    assert len(inspection.atoms) == 3


def test_diagnostics_and_coverage_are_non_mutating() -> None:
    diagnostics = registry.call(
        "cf.get_compile_diagnostics",
        text="TITLE PAGE\n\nINT. ROOM - DAY\n\nA lamp flickers.\n",
    )
    coverage = registry.call(
        "cf.audit_script_coverage",
        text="TITLE PAGE\n\nINT. ROOM - DAY\n\nA lamp flickers.\n",
    )
    assert any(item.code == "CF_PARSE_CONTENT_BEFORE_SCENE" for item in diagnostics)
    assert coverage.uncovered_non_whitespace_bytes > 0


def test_registry_fails_closed_for_unknown_tools_and_scenes() -> None:
    with pytest.raises(KeyError, match="Unknown MCP tool"):
        registry.call("cf.mutate_canon", text=SCRIPT)

    with pytest.raises(KeyError, match="Scene not found"):
        registry.call(
            "cf.inspect_scene",
            text=SCRIPT,
            scene_id="00000000-0000-0000-0000-000000000000",
        )
