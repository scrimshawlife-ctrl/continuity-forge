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
