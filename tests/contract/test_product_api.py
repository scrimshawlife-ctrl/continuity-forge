"""Product workflow API adapters — wrap kernel breakdown without breaking cf.breakdown.v1."""

from __future__ import annotations

from pathlib import Path

from continuity_forge_api.main import app
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).resolve().parents[1] / "golden" / "fixtures" / "continuity.fountain"


def test_product_create_analyze_prepare_export_path() -> None:
    client = TestClient(app)
    text = FIXTURE.read_text(encoding="utf-8")
    created = client.post(
        "/v1/product/create-project",
        json={"title": "Night Run", "production_type": "Short Film", "text": text},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["document_key"]
    assert body["phase"] == "IMPORTED"

    analyze = client.post(
        "/v1/product/analyze",
        json={
            "title": "Night Run",
            "text": text,
            "document_key": body["document_key"],
            "format": "fountain",
            "production_type": "Short Film",
        },
    )
    assert analyze.status_code == 200
    payload = analyze.json()
    assert payload["summary"]["counts"]["scenes"] >= 1
    assert payload["breakdown"]["schema_version"] == "cf.breakdown.v1"
    assert payload["scenes"]
    scene_id = payload["scenes"][0]["scene_id"]

    detail = client.post(
        f"/v1/product/scenes/{scene_id}",
        json={
            "title": "Night Run",
            "text": text,
            "document_key": body["document_key"],
            "format": "fountain",
        },
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["shots"] is not None

    prep = client.post(
        f"/v1/product/scenes/{scene_id}/prepare",
        json={
            "title": "Night Run",
            "text": text,
            "document_key": body["document_key"],
            "format": "fountain",
            "scene_id": scene_id,
            "warnings_acknowledged": True,
        },
    )
    assert prep.status_code == 200
    assert prep.json()["provider_neutral"] is True
    assert prep.json()["package"]["schema_version"] == "cf.scene_package.v1"
    assert "openai_payload" not in prep.json()["package"]


def test_product_empty_script_friendly_error() -> None:
    client = TestClient(app)
    res = client.post(
        "/v1/product/analyze",
        json={"title": "Empty", "text": "   ", "format": "fountain"},
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert detail["data_preserved"] is True
    assert detail["technical_detail"] or detail["what_happened"]
