from continuity_forge_api.main import app
from continuity_forge_operator import DEFAULT_PROJECT_STORE
from fastapi.testclient import TestClient


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
    assert TestClient(app).get("/health").json() == {"status": "ok"}


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
    assert DEFAULT_PROJECT_STORE.get_project(key) is not None


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
