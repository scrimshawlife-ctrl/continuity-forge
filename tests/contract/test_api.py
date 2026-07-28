from fastapi.testclient import TestClient

from continuity_forge_api.main import app


def test_compile_endpoint_returns_result_envelope() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/compile",
        json={"title": "Test", "text": "INT. ROOM - DAY\n\nA lamp flickers.\n"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["scenes"][0]["slugline"] == "INT. ROOM - DAY"
    assert "coverage" in payload
    assert "diagnostics" in payload


def test_compile_endpoint_rejects_unsupported_source_format() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/compile",
        json={
            "title": "Test",
            "text": "INT. ROOM - DAY\n",
            "source_format": "docx",
        },
    )
    assert response.status_code == 422
