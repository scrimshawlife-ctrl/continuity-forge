from continuity_forge_api.main import app
from continuity_forge_runtime import get_runtime
from fastapi.testclient import TestClient

CONTINUITY_SAMPLE = """Title: Continuity Sample

INT. SAFEHOUSE - NIGHT

Mara enters with a red keycard.

MARA
If the jacket changes, the timeline is lying.

INT. ALLEY - CONTINUOUS

Mara still wears the jacket. The red keycard remains.

MARA
Keep rolling.

INT. SAFEHOUSE - LATER

Mara re-enters. The red keycard is gone.
"""


def test_compile_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/compile",
        json={
            "title": "Test",
            "document_key": "api-test",
            "text": "INT. ROOM - DAY\n\nA lamp flickers.\n",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenes"][0]["slugline"] == "INT. ROOM - DAY"
    assert payload["coverage"]["ratio"] == 1.0
    assert payload["diagnostics"] == []


def test_health_endpoint() -> None:
    payload = TestClient(app).get("/health").json()
    assert payload["status"] == "ok"
    assert "backend" in payload


def test_compile_endpoint_accepts_fdx() -> None:
    source = (
        '<FinalDraft><Content><Paragraph Type="Scene Heading"><Text>INT. LAB - DAY</Text>'
        "</Paragraph></Content></FinalDraft>"
    )
    response = TestClient(app).post(
        "/v1/compile",
        json={"text": source, "format": "fdx", "document_key": "api-fdx"},
    )
    assert response.status_code == 200
    assert response.json()["format"] == "fdx"


def test_compile_endpoint_rejects_unknown_format() -> None:
    response = TestClient(app).post(
        "/v1/compile",
        json={"text": "anything", "format": "pdf"},
    )
    assert response.status_code == 422


def test_continuity_ledger_endpoint() -> None:
    response = TestClient(app).post(
        "/v1/continuity-ledger",
        json={
            "document_key": "api-ledger",
            "text": (
                "INT. ROOM - DAY\n\n"
                "Mara enters with a red keycard.\n\n"
                "MARA\nThis is the plant.\n\n"
                "EXT. ALLEY - NIGHT\n\n"
                "The red keycard payoff sits on the crate.\n"
            ),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["entities"]
    assert payload["scene_contracts"]
    assert any(entity["kind"] == "character" for entity in payload["entities"])


def test_project_ingest_and_generate_flow() -> None:
    client = TestClient(app)
    # Isolate default store side effects by using unique keys
    key = "api-project-flow"
    lease = client.post(
        "/v1/projects/lease",
        json={"document_key": key, "holder": "api"},
    )
    assert lease.status_code == 200
    ingest = client.post(
        "/v1/projects/ingest",
        json={
            "document_key": key,
            "actor_id": "api",
            "authorization_scope": "kernel:pipeline",
            "idempotency_key": "api-ingest-1",
            "rationale": "contract",
            "text": "INT. ROOM - DAY\n\nMara enters with a red keycard.\n\nMARA\nGo.\n",
        },
    )
    assert ingest.status_code == 200
    status = client.get(f"/v1/projects/{key}/status")
    assert status.status_code == 200
    shot_id = ingest.json()["project"]["shot_contracts"]["contracts"][0]["shot_id"]
    preview = client.post(
        "/v1/generate/preview",
        json={
            "document_key": key,
            "shot_id": shot_id,
            "seed": "1",
            "actor_id": "api",
            "authorization_scope": "generation:preview",
            "idempotency_key": "gen-1",
            "rationale": "preview",
        },
    )
    assert preview.status_code == 200
    assert preview.json()["authority"] == "PROPOSED"
    loop = client.post(
        "/v1/generate/repair-loop",
        json={
            "document_key": key,
            "shot_id": shot_id,
            "seed": "1",
            "fail_first": True,
            "actor_id": "api",
            "authorization_scope": "generation:repair",
            "idempotency_key": "loop-1",
            "rationale": "loop",
        },
    )
    assert loop.status_code == 200
    assert loop.json()["status"] == "accepted_proposed"
    # Projects are tenant-scoped (anonymous::<key> when auth is off).
    assert get_runtime().project_store.get_project(f"anonymous::{key}") is not None


def test_pipeline_run_endpoint_is_idempotent() -> None:
    client = TestClient(app)
    body = {
        "actor_id": "api-tester",
        "authorization_scope": "kernel:pipeline",
        "idempotency_key": "api-pipeline-1",
        "rationale": "API contract test",
        "document_key": "api-pipeline",
        "text": "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n",
    }
    first = client.post("/v1/pipeline/runs", json=body)
    second = client.post("/v1/pipeline/runs", json=body)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] == second.json()["run_id"]
    assert first.json()["status"] == "completed"
    run_id = first.json()["run_id"]
    fetched = client.get(f"/v1/pipeline/runs/{run_id}")
    assert fetched.status_code == 200
    assert fetched.json()["artifacts"]["shot_contracts"]["contracts"]
    manifest = client.get("/v1/pipeline/temporal-manifest")
    assert manifest.status_code == 200
    assert manifest.json()["workflow_type"] == "KernelPipelineWorkflow"

    events = client.get(f"/v1/pipeline/runs/{run_id}/events")
    assert events.status_code == 200
    page = events.json()
    assert page["claim"] == "workflow_events_observability_not_canon"
    assert page["transport"] == "poll"
    assert page["workflow_complete_is_not_production_ready"] is True
    assert page["events"]
    assert page["events"][0]["kind"] == "run_started"
    assert page["events"][-1]["kind"] == "run_completed"
    assert page["progress"]["percent"] == 100
    assert "red keycard" not in events.text  # no script body leak
    # Resume cursor: after first event
    first_id = page["events"][0]["event_id"]
    resumed = client.get(
        f"/v1/pipeline/runs/{run_id}/events",
        params={"last_event_id": first_id},
    )
    assert resumed.status_code == 200
    assert resumed.json()["events"][0]["sequence"] == 2


def test_shot_contracts_endpoint() -> None:
    response = TestClient(app).post(
        "/v1/shot-contracts",
        json={
            "document_key": "api-shots",
            "text": (
                "INT. ROOM - DAY\n\n"
                "Mara enters with a red keycard.\n\n"
                "MARA\nHold the line.\n\n"
                "EXT. ROOF - NIGHT\n\n"
                "The red keycard is gone.\n"
            ),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["contracts"]) == 2
    assert payload["contracts"][0]["required_atom_ids"]
    assert payload["contracts"][0]["start_state_hash"]
    assert payload["ledger_hash"]


def test_list_projects_endpoint() -> None:
    client = TestClient(app)
    # Seed via proof so a tenant-scoped project exists under anonymous::
    proof = client.post(
        "/v1/proof",
        json={
            "title": "List Seed",
            "document_key": "list-seed",
            "text": "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n",
            "seed": "list",
            "actor_id": "api-list",
        },
    )
    assert proof.status_code == 200
    listed = client.get("/v1/projects")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["tenant_id"] == "anonymous"
    keys = {row["document_key"] for row in payload["projects"]}
    assert "anonymous::list-seed" in keys
    row = next(r for r in payload["projects"] if r["document_key"] == "anonymous::list-seed")
    assert row["scene_count"] >= 1
    assert row["shot_count"] >= 1
    assert row["source_hash"]
    assert row["state_hash"]


def test_controlled_proof_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/proof",
        json={
            "title": "Continuity Sample",
            "document_key": "api-proof-ui",
            "text": CONTINUITY_SAMPLE,
            "seed": "ui-contract",
            "budget_seconds": 60,
            "actor_id": "api-proof",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "m7.proof.v1"
    assert payload["claim"] == "controlled_proof_not_production_ready"
    assert payload["receipt_hash"]
    assert payload["within_budget"] is True
    assert payload["shots"]
    assert payload["shots"][0]["attempts"] >= 2
    assert "anonymous::api-proof-ui" in payload["document_key"]
    assert payload["cost_ledger"] is not None
    assert payload["cost_summary"] is not None
    assert payload["cost_ledger"]["claim"] == "cost_ledger_run_provenance_not_canon"
    assert payload["cost_summary"]["event_count"] >= 1
    assert payload["cost_summary"]["retry_event_count"] >= 1
    assert payload["cost_summary"]["by_provider"].get("mock", 0) >= 1
    assert all(e["authority"] == "PROPOSED" for e in payload["cost_ledger"]["events"])


def test_web_ui_is_served() -> None:
    client = TestClient(app)
    index = client.get("/")
    assert index.status_code == 200
    assert "Run a proof" in index.text or "Build breakdown" in index.text
    assert "Build breakdown" in index.text
    assert "Run proof" in index.text
    assert "Import file" in index.text
    assert 'id="btn-import"' in index.text
    assert 'id="script-file"' in index.text
    assert "Download breakdown JSON" in index.text
    assert 'id="btn-breakdown"' in index.text
    assert "controlled_proof_not_production_ready" in index.text
    assert 'id="claim-post-proof"' in index.text
    assert "not ready — mock controlled proof only" in index.text
    assert "Approval queue empty" in index.text
    assert "Request approval" in index.text
    assert "Repair / rationale" in index.text
    assert 'id="scene-nav"' in index.text
    assert "All scenes" in index.text
    assert 'id="shot-empty"' in index.text
    assert 'id="shot-virtual"' in index.text
    assert "Virtualize rows" in index.text
    assert 'id="shot-filter-status"' in index.text
    assert "Preview stale" in index.text
    assert ">Stale<" in index.text or "Stale</th>" in index.text
    assert 'id="canon"' in index.text
    assert 'id="control"' in index.text
    assert "Acquire lease" in index.text
    assert "Compile incremental" in index.text
    assert 'id="btn-compile-incremental"' in index.text
    assert 'id="receipt-budget"' in index.text
    assert 'id="cost-panel"' in index.text
    assert 'id="claim-budget-label"' in index.text
    assert "Cost ledger" in index.text
    styles = client.get("/styles.css")
    assert styles.status_code == 200
    assert "Hallmark" in styles.text
    assert "claim-banner--post-proof" in styles.text
    assert "cost-panel" in styles.text
    tokens = client.get("/tokens.css")
    assert tokens.status_code == 200
    assert "--color-accent" in tokens.text
    assert "Terminal" in tokens.text
    app_js = client.get("/app.js")
    assert app_js.status_code == 200
    assert "/v1/proof" in app_js.text
    assert "/v1/projects" in app_js.text
    assert "controlled_proof_not_production_ready" in app_js.text
    assert "repairRationaleSummary" in app_js.text
    assert "Approval queue empty" in app_js.text or "approval-empty" in app_js.text
    assert "not production ready" in app_js.text
    assert "buildSceneIndex" in app_js.text
    assert "setSceneFocus" in app_js.text
    assert "scene_id" in app_js.text
    assert "logicalShots" in app_js.text
    assert "renderShotTableVirtual" in app_js.text
    assert "useVirtualization" in app_js.text
    assert "virtualThreshold" in app_js.text
    assert "/v1/compile/incremental" in app_js.text
    assert "compileIncremental" in app_js.text
    assert "lastCompiledDocument" in app_js.text
    assert "renderCostPanel" in app_js.text
    assert "over budget" in app_js.text
    assert "cost_summary" in app_js.text
    assert "/v1/breakdown" in app_js.text
    assert "buildBreakdown" in app_js.text
    assert "exportBreakdownJson" in app_js.text
    assert "importScriptFile" in app_js.text
    assert 'id="workflow-panel"' in index.text
    assert "workflow complete ≠ production ready" in index.text or (
        "workflow complete" in index.text and "production ready" in index.text
    )
    assert "pollWorkflowEvents" in app_js.text
    assert "/events" in app_js.text
    assert "workflow_complete" in app_js.text or "not production ready" in app_js.text


def test_health_reports_version() -> None:
    payload = TestClient(app).get("/health").json()
    assert payload["version"] == "1.5.1"


def test_compile_incremental_endpoint() -> None:
    client = TestClient(app)
    text = "INT. ROOM - DAY\n\nA lamp flickers.\n"
    first = client.post(
        "/v1/compile/incremental",
        json={
            "title": "Inc",
            "document_key": "api-inc",
            "text": text,
        },
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["claim"] == "incremental_compile_not_production_ready"
    assert payload["mode"] == "incremental"
    assert payload["prior_reconciled"] is False
    assert len(payload["recompiled_scene_ids"]) == len(payload["document"]["scenes"])
    assert payload["coverage_accounted_characters"] == payload["coverage_source_characters"]
    assert "PROPOSED" in payload["authority_note"] or "canon" in payload["authority_note"].lower()

    second = client.post(
        "/v1/compile/incremental",
        json={
            "title": "Inc",
            "document_key": "api-inc",
            "text": text,
            "prior_document": payload["document"],
        },
    )
    assert second.status_code == 200
    carried = second.json()
    assert carried["prior_reconciled"] is True
    assert carried["carried_scene_ids"]
    assert carried["recompiled_scene_ids"] == []
    assert carried["stale_shot_ids"] == []
    assert carried["document"]["source_hash"] == payload["document"]["source_hash"]


def test_invalidation_preview_endpoint() -> None:
    client = TestClient(app)
    source = CONTINUITY_SAMPLE
    # Compile once to learn a scene id via shot contracts
    shots = client.post(
        "/v1/shot-contracts",
        json={"title": "Inv", "document_key": "inv-prev", "text": source},
    )
    assert shots.status_code == 200
    scene_id = shots.json()["contracts"][0]["scene_id"]
    response = client.post(
        "/v1/invalidation/preview",
        json={
            "title": "Inv",
            "document_key": "inv-prev",
            "text": source,
            "change": {"scene_ids": [scene_id]},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["claim"] == "invalidation_preview_not_a_canon_write"
    assert payload["report"]["stale_ids"]
    assert payload["stale_shot_ids"]
    assert "PROPOSED" in payload["report"]["authority_note"]


def test_lease_approvals_and_runs_endpoints() -> None:
    client = TestClient(app)
    key = "control-flow"
    # Seed project via proof (lease acquired/released inside runner).
    proof = client.post(
        "/v1/proof",
        json={
            "title": "Control",
            "document_key": key,
            "text": "INT. ROOM - DAY\n\nMara enters.\n\nMARA\nGo.\n",
            "seed": "ctrl",
            "actor_id": "proof-ui",
        },
    )
    assert proof.status_code == 200

    empty = client.get(f"/v1/projects/{key}/lease")
    assert empty.status_code == 200
    assert empty.json()["active"] is False

    lease = client.post(
        "/v1/projects/lease",
        json={"document_key": key, "holder": "proof-ui", "ttl_seconds": 300},
    )
    assert lease.status_code == 200
    assert lease.json()["holder"] == "proof-ui"

    got = client.get(f"/v1/projects/{key}/lease")
    assert got.status_code == 200
    assert got.json()["active"] is True

    approval = client.post(
        "/v1/approvals/request",
        json={
            "document_key": key,
            "kind": "commit_candidate",
            "actor_id": "proof-ui",
            "authorization_scope": "approvals",
            "idempotency_key": "appr-1",
            "rationale": "contract",
        },
    )
    assert approval.status_code == 200
    approval_id = approval.json()["approval_id"]

    listed = client.get(f"/v1/projects/{key}/approvals")
    assert listed.status_code == 200
    assert len(listed.json()["approvals"]) == 1

    decided = client.post(
        "/v1/approvals/decide",
        json={
            "approval_id": approval_id,
            "status": "granted",
            "actor_id": "proof-ui",
            "authorization_scope": "approvals",
            "idempotency_key": "dec-1",
            "rationale": "ok",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "granted"

    runs = client.get(f"/v1/projects/{key}/runs")
    assert runs.status_code == 200
    # proof stores under tenant-scoped key; runs may be empty if pipeline key differs
    assert "runs" in runs.json()

    released = client.delete(f"/v1/projects/{key}/lease?holder=proof-ui")
    assert released.status_code == 200
    assert released.json()["status"] == "released"
