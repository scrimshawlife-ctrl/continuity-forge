"""Authored playbook regression checks; never contacts live services."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_writing_skills_have_standalone_procedure_and_real_ingest_route():
    for name in ("kubrick", "scriptwriting"):
        skill = ROOT / "skills" / name
        body = (skill / "SKILL.md").read_text().lower()
        assert "same as base" not in body
        assert "same 1-5 rubric" not in body
        assert (skill / "references/standalone-procedure.md").is_file()
        integration = (skill / "references/continuity-forge-integration.md").read_text()
        assert "continuity-forge ingest " not in integration
        assert "finally:" in integration
        assert "expected_state_hash=" in integration


def test_operator_quick_path_separates_mcp_and_rest():
    body = (ROOT / "skills/hermes-continuity-forge/SKILL.md").read_text()
    assert "MCP uses `source`; REST uses `text`" in body
    workflows = (ROOT / "skills/hermes-continuity-forge/references/workflows.md").read_text()
    assert 'authorization_scope="generation:repair"' in workflows
    assert 'authorization_scope="generation:preview"' in workflows
    assert "finally:" in workflows


def test_exact_mcp_recipes_execute_in_isolated_runtime(monkeypatch, tmp_path):
    import ast
    import inspect
    import re

    from continuity_forge_auth import AuthService
    from continuity_forge_harness import RunStore
    from continuity_forge_mcp import server
    from continuity_forge_operator import ProjectStore
    from continuity_forge_providers import ArtifactStore, ProviderGateway
    from continuity_forge_runtime.factory import RuntimeContext

    runs = RunStore()
    runtime = RuntimeContext(
        runs,
        ProjectStore(run_store=runs),
        ProviderGateway(),
        AuthService(),
        ArtifactStore(tmp_path / "artifacts"),
        "test",
    )
    monkeypatch.setattr(server, "_rt", lambda: runtime)
    names = [
        "acquire_write_lease",
        "release_write_lease",
        "get_project_status",
        "ingest_script",
        "queue_generation",
        "run_shot_repair_loop",
    ]
    scope = {name: getattr(server, name) for name in names}
    scope.update(
        DOC="recipe-test",
        ACTOR="recipe-actor",
        INTENT="ingest-1",
        REPAIR_INTENT="repair-1",
        SOURCE="INT. ROOM - DAY\n\nMara returns a key.\n",
    )
    guide = ROOT / "skills/kubrick/references/continuity-forge-integration.md"
    snippets = re.findall(r"```python\n(.*?)```", guide.read_text(), re.DOTALL)
    workflows = ROOT / "skills/hermes-continuity-forge/references/workflows.md"
    snippets += re.findall(r"```python\n(.*?)```", workflows.read_text(), re.DOTALL)
    for index, snippet in enumerate(snippets):
        for node in ast.walk(ast.parse(snippet)):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in names
            ):
                inspect.signature(scope[node.func.id]).bind(**{k.arg: None for k in node.keywords})
        scope["INTENT"] = f"recipe-{index}"
        if "queue_generation" in snippet:
            project = runtime.project_store.get_project(scope["DOC"])
            scope["SHOT"] = project.shot_contracts["contracts"][0]["shot_id"]
        # Execute repository-owned recipe text only, never fetched/user-supplied code.
        exec(compile(snippet, str(guide), "exec"), scope)  # noqa: S102 — trusted repo recipes only
    assert scope["candidate"]["authority"] == "PROPOSED"
    assert scope["repair"]["status"] == "accepted_proposed"
    assert (
        server.acquire_write_lease("recipe-test", "different-actor")["holder"] == "different-actor"
    )
    server.release_write_lease("recipe-test", "different-actor")
