import os

from continuity_forge_api.main import app
from continuity_forge_auth import bootstrap_dev_tenant
from continuity_forge_runtime import get_runtime, reset_runtime
from fastapi.testclient import TestClient


def test_whoami_anonymous_when_auth_not_required() -> None:
    os.environ.pop("CF_AUTH_REQUIRED", None)
    reset_runtime()
    client = TestClient(app)
    response = client.get("/v1/whoami")
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "anonymous"


def test_auth_required_rejects_missing_key() -> None:
    os.environ["CF_AUTH_REQUIRED"] = "1"
    try:
        reset_runtime()
        client = TestClient(app)
        response = client.get("/v1/whoami")
        assert response.status_code == 401
        bootstrap_dev_tenant(get_runtime().auth, tenant_id="dev", api_key="dev-local-key")
        ok = client.get("/v1/whoami", headers={"Authorization": "Bearer dev-local-key"})
        assert ok.status_code == 200
        assert ok.json()["tenant_id"] == "dev"
    finally:
        os.environ.pop("CF_AUTH_REQUIRED", None)
        reset_runtime()


def test_tenant_scoped_ingest_isolation() -> None:
    os.environ.pop("CF_AUTH_REQUIRED", None)
    reset_runtime()
    bootstrap_dev_tenant(get_runtime().auth, tenant_id="alpha", api_key="alpha-key")
    bootstrap_dev_tenant(get_runtime().auth, tenant_id="beta", api_key="beta-key")
    client = TestClient(app)
    # Acquire lease + ingest under alpha
    headers = {"Authorization": "Bearer alpha-key"}
    assert (
        client.post(
            "/v1/projects/lease",
            headers=headers,
            json={"document_key": "shared-name", "holder": "alpha-actor"},
        ).status_code
        == 200
    )
    ingest = client.post(
        "/v1/projects/ingest",
        headers=headers,
        json={
            "document_key": "shared-name",
            "actor_id": "alpha-actor",
            "authorization_scope": "kernel:pipeline",
            "idempotency_key": "alpha-1",
            "rationale": "tenant isolation",
            "text": "INT. A - DAY\n\nAlpha only.\n",
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["tenant_id"] == "alpha"
    # Beta cannot see alpha's project under the same logical document_key
    beta = client.get(
        "/v1/projects/shared-name/status",
        headers={"Authorization": "Bearer beta-key"},
    )
    assert beta.status_code == 404
