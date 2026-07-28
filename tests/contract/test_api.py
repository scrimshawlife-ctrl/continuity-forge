from continuity_forge_api.main import app
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
