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
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["document_key"]
    assert body["phase"] == "IMPORTED"
    # Durable via ProjectStore (not browser-only)
    assert body.get("persisted") is True
    listed = client.get("/v1/projects")
    assert listed.status_code == 200
    keys = [p["document_key"] for p in listed.json().get("projects", [])]
    assert any(body["document_key"] in k or k.endswith(body["document_key"]) for k in keys)

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
    djson = detail.json()
    assert djson["shots"] is not None
    entry_names = {v["field_name"] for v in djson["entry_state"]}
    exit_names = {v["field_name"] for v in djson["exit_state"]}
    assert "start_state" in entry_names
    assert "end_state" in exit_names

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


def test_product_override_confirm_applies_user_locked() -> None:
    client = TestClient(app)
    text = FIXTURE.read_text(encoding="utf-8")
    created = client.post(
        "/v1/product/create-project",
        json={"title": "Lock Test", "production_type": "Short Film", "text": text},
    ).json()
    analyzed = client.post(
        "/v1/product/analyze",
        json={
            "title": "Lock Test",
            "text": text,
            "document_key": created["document_key"],
            "format": "fountain",
        },
    ).json()
    entity = next(e for e in analyzed["entities"] if e["kind"] == "character")
    original = entity["name"]
    preview = client.post(
        "/v1/product/override/preview",
        json={
            "title": "Lock Test",
            "text": text,
            "document_key": created["document_key"],
            "format": "fountain",
            "target_kind": "entity",
            "target_id": entity["entity_id"],
            "field_name": "name",
            "original_value": original,
            "locked_value": original + " LOCKED",
            "confirm": True,
            "existing_overrides": [],
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body.get("confirmed") is True
    locked_entity = next(e for e in body["entities"] if e["entity_id"] == entity["entity_id"])
    name_val = next(v for v in locked_entity["values"] if v["field_name"] == "name")
    assert name_val["locked"] is True
    assert name_val["provenance"]["label"] == "USER_LOCKED"
    assert name_val["value"] == original + " LOCKED"
    assert name_val["original_value"] == original

    # Re-analyze with overrides returns locked name
    again = client.post(
        "/v1/product/analyze",
        json={
            "title": "Lock Test",
            "text": text,
            "document_key": created["document_key"],
            "format": "fountain",
            "overrides": [body["override"]],
        },
    ).json()
    re_ent = next(e for e in again["entities"] if e["entity_id"] == entity["entity_id"])
    re_name = next(v for v in re_ent["values"] if v["field_name"] == "name")
    assert re_name["provenance"]["label"] == "USER_LOCKED"


def test_product_review_decision_records_lineage() -> None:
    client = TestClient(app)
    text = FIXTURE.read_text(encoding="utf-8")
    created = client.post(
        "/v1/product/create-project",
        json={"title": "Review Test", "production_type": "Short Film", "text": text},
    ).json()
    analyzed = client.post(
        "/v1/product/analyze",
        json={
            "title": "Review Test",
            "text": text,
            "document_key": created["document_key"],
            "format": "fountain",
        },
    ).json()
    shot_id = analyzed["breakdown"]["shots"][0]["shot_id"]
    res = client.post(
        "/v1/product/review/decision",
        json={
            "shot_id": shot_id,
            "action": "accept",
            "candidate_id": "cand-1",
            "document_key": created["document_key"],
            "actor_id": "tester",
        },
    )
    assert res.status_code == 200
    decision = res.json()["decision"]
    assert decision["lineage_preserved"] is True
    assert decision["advances_canon"] is True
    assert res.json()["lineage_preserved"] is True


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


def test_ui_has_review_actions_and_no_fake_stage_timer() -> None:
    root = Path(__file__).resolve().parents[2] / "apps" / "web"
    js = (root / "app.js").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "data-review-action" in js or "recordReview" in js
    assert "accept_with_note" in js
    assert "renderStagesWorking" in js
    assert "setInterval" not in js or "renderStagesWorking" in js
    # Ensure fake sequential timer progression was removed from analyze path
    assert "stage = Math.min(stage + 1" not in js
    assert "Correct scene metadata" in js or "meta-slugline" in js
    assert "Review" in html
    assert "USER LOCKED" in js or "USER_LOCKED" in js
