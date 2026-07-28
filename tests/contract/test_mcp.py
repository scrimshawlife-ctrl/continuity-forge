from continuity_forge_mcp.server import (
    audit_script_coverage,
    build_ledger,
    build_shot_contracts,
    compile_script,
    get_compile_diagnostics,
    get_pipeline_run,
    get_pipeline_run_events,
    get_scene,
    get_temporal_manifest,
    list_entities,
    list_scenes,
    list_setup_payoff_links,
    list_shot_summaries,
    run_kernel_pipeline,
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


def test_mcp_ledger_tools() -> None:
    source = (
        "INT. ROOM - DAY\n\n"
        "Mara enters holding a brass compass.\n\n"
        "MARA\nThis is the plant.\n\n"
        "EXT. ROOF - NIGHT\n\n"
        "The brass compass payoff gleams.\n"
    )
    ledger = build_ledger(source, document_key="mcp-ledger")
    entities = list_entities(source, document_key="mcp-ledger")
    links = list_setup_payoff_links(source, document_key="mcp-ledger")
    assert ledger["entities"] == entities
    assert any(entity["kind"] == "prop" for entity in entities)
    assert links == ledger["setup_payoff_links"]


def test_mcp_shot_contract_tools() -> None:
    source = (
        "INT. ROOM - DAY\n\n"
        "Mara enters holding a brass compass.\n\n"
        "MARA\nThis is the plant.\n\n"
        "EXT. ROOF - NIGHT\n\n"
        "The brass compass payoff gleams.\n"
    )
    bundle = build_shot_contracts(source, document_key="mcp-shots")
    summaries = list_shot_summaries(source, document_key="mcp-shots")
    assert len(bundle["contracts"]) == 2
    assert len(summaries) == 2
    assert summaries[0]["shot_id"] == bundle["contracts"][0]["shot_id"]
    assert summaries[0]["constraint_count"] >= 1


def test_mcp_pipeline_tools() -> None:
    source = "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n"
    run = run_kernel_pipeline(
        source,
        actor_id="mcp-tester",
        authorization_scope="kernel:pipeline",
        idempotency_key="mcp-pipeline-1",
        rationale="MCP contract test",
        document_key="mcp-pipeline",
    )
    assert run["status"] == "completed"
    fetched = get_pipeline_run(run["run_id"])
    assert fetched is not None
    assert fetched["run_id"] == run["run_id"]
    events = get_pipeline_run_events(run["run_id"])
    assert events is not None
    assert events["claim"] == "workflow_events_observability_not_canon"
    assert events["workflow_complete_is_not_production_ready"] is True
    assert events["events"][0]["kind"] == "run_started"
    assert events["progress"]["percent"] == 100
    resumed = get_pipeline_run_events(run["run_id"], last_event_id=events["events"][0]["event_id"])
    assert resumed is not None
    assert resumed["events"][0]["sequence"] == 2
    manifest = get_temporal_manifest()
    assert manifest["task_queue"] == "continuity-forge-kernel"
