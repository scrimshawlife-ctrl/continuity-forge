from fastapi.testclient import TestClient

from continuity_forge_api.main import app


def test_compile_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/compile",
        json={"title": "Test", "text": "INT. ROOM - DAY\n\nA lamp flickers.\n"},
    )
    assert response.status_code == 200
    assert response.json()["scenes"][0]["slugline"] == "INT. ROOM - DAY"
