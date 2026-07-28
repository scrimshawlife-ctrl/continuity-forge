"""Contract tests for breakdown handoff API."""

from continuity_forge_api.main import app
from fastapi.testclient import TestClient

SAMPLE = """Title: Handoff Sample

INT. ROOM - DAY

Mara enters with a red keycard.

MARA
Hold the line.

EXT. ROOF - NIGHT

The red keycard is gone.
"""


def test_breakdown_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/breakdown",
        json={
            "title": "Handoff Sample",
            "document_key": "api-breakdown",
            "text": SAMPLE,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "cf.breakdown.v1"
    assert payload["claim"] == "shot_breakdown_with_continuity_not_production_film"
    assert payload["shot_count"] == 2
    assert payload["scene_count"] == 2
    assert payload["package_hash"]
    assert payload["shots"][0]["slugline"] == "INT. ROOM - DAY"
    assert "PROPOSED" in payload["authority_note"] or "canon" in payload["authority_note"].lower()


def test_breakdown_markdown_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/breakdown/markdown",
        json={"title": "MD", "text": SAMPLE, "document_key": "api-bd-md"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["shot_count"] == 2
    assert "Shot-by-shot" in payload["markdown"]
    assert payload["package_hash"]
