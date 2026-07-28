import os

from continuity_forge_api.main import app
from continuity_forge_auth import bootstrap_dev_tenant
from continuity_forge_runtime import get_runtime, reset_runtime
from fastapi.testclient import TestClient


def _clear_bootstrap_env() -> None:
    os.environ.pop("CF_BOOTSTRAP_DEV_TENANT", None)
    os.environ.pop("CF_ENV", None)
    os.environ.pop("ENVIRONMENT", None)


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
    """Tenant B cannot read tenant A's document under the same logical key."""
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


def test_tenant_a_cannot_read_or_write_tenant_b_document_keys() -> None:
    """Cross-tenant read/write isolation for the same logical document key."""
    os.environ.pop("CF_AUTH_REQUIRED", None)
    reset_runtime()
    bootstrap_dev_tenant(get_runtime().auth, tenant_id="tenant-a", api_key="key-a")
    bootstrap_dev_tenant(get_runtime().auth, tenant_id="tenant-b", api_key="key-b")
    client = TestClient(app)
    headers_a = {"Authorization": "Bearer key-a"}
    headers_b = {"Authorization": "Bearer key-b"}
    doc = "isolation-doc"

    # Tenant A writes
    assert (
        client.post(
            "/v1/projects/lease",
            headers=headers_a,
            json={"document_key": doc, "holder": "actor-a"},
        ).status_code
        == 200
    )
    ingest_a = client.post(
        "/v1/projects/ingest",
        headers=headers_a,
        json={
            "document_key": doc,
            "actor_id": "actor-a",
            "authorization_scope": "kernel:pipeline",
            "idempotency_key": "a-write-1",
            "rationale": "tenant-a write",
            "text": "INT. TENANT A - DAY\n\nOwned by A.\n",
            "title": "Tenant A Script",
        },
    )
    assert ingest_a.status_code == 200
    assert ingest_a.json()["tenant_id"] == "tenant-a"
    a_project_key = ingest_a.json()["project"]["document_key"]
    assert a_project_key == "tenant-a::isolation-doc"

    # Tenant B cannot read A's project via logical key
    assert client.get(f"/v1/projects/{doc}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/projects/{doc}/status", headers=headers_b).status_code == 404
    assert client.get(f"/v1/projects/{doc}/runs", headers=headers_b).status_code == 200
    runs_b = client.get(f"/v1/projects/{doc}/runs", headers=headers_b).json()
    assert runs_b["document_key"] == "tenant-b::isolation-doc"
    assert runs_b["runs"] == []

    # Tenant B cannot read by spoofing A's scoped key in the path
    spoof = client.get("/v1/projects/tenant-a::isolation-doc", headers=headers_b)
    assert spoof.status_code == 404

    # Tenant B write creates a *separate* project; does not overwrite A
    assert (
        client.post(
            "/v1/projects/lease",
            headers=headers_b,
            json={"document_key": doc, "holder": "actor-b"},
        ).status_code
        == 200
    )
    ingest_b = client.post(
        "/v1/projects/ingest",
        headers=headers_b,
        json={
            "document_key": doc,
            "actor_id": "actor-b",
            "authorization_scope": "kernel:pipeline",
            "idempotency_key": "b-write-1",
            "rationale": "tenant-b write must not clobber A",
            "text": "INT. TENANT B - DAY\n\nOwned by B.\n",
            "title": "Tenant B Script",
        },
    )
    assert ingest_b.status_code == 200
    assert ingest_b.json()["tenant_id"] == "tenant-b"
    assert ingest_b.json()["project"]["document_key"] == "tenant-b::isolation-doc"
    assert ingest_b.json()["project"]["title"] == "Tenant B Script"

    # Tenant A still sees original content
    still_a = client.get(f"/v1/projects/{doc}", headers=headers_a)
    assert still_a.status_code == 200
    body_a = still_a.json()
    assert body_a["document_key"] == "tenant-a::isolation-doc"
    assert body_a["title"] == "Tenant A Script"

    # List endpoints are tenant-filtered
    list_a = client.get("/v1/projects", headers=headers_a).json()
    list_b = client.get("/v1/projects", headers=headers_b).json()
    assert list_a["tenant_id"] == "tenant-a"
    assert list_b["tenant_id"] == "tenant-b"
    keys_a = {p["document_key"] for p in list_a["projects"]}
    keys_b = {p["document_key"] for p in list_b["projects"]}
    assert "tenant-a::isolation-doc" in keys_a
    assert "tenant-b::isolation-doc" not in keys_a
    assert "tenant-b::isolation-doc" in keys_b
    assert "tenant-a::isolation-doc" not in keys_b

    # Tenant B cannot acquire lease on A's storage key via spoofed path key
    lease_spoof = client.post(
        "/v1/projects/lease",
        headers=headers_b,
        json={"document_key": "tenant-a::isolation-doc", "holder": "actor-b-spoof"},
    )
    assert lease_spoof.status_code == 200
    # Lease is created under B's re-scoped key, not A's
    assert lease_spoof.json()["document_key"] == "tenant-b::tenant-a::isolation-doc"
    lease_a = client.get(f"/v1/projects/{doc}/lease", headers=headers_a).json()
    assert lease_a["document_key"] == "tenant-a::isolation-doc"
    # A's lease holder must not become the spoof holder
    if lease_a.get("lease"):
        assert lease_a["lease"]["holder"] != "actor-b-spoof"


def test_bootstrap_dev_disabled_without_flag() -> None:
    os.environ.pop("CF_AUTH_REQUIRED", None)
    _clear_bootstrap_env()
    try:
        reset_runtime()
        client = TestClient(app)
        response = client.post("/v1/tenants/bootstrap-dev")
        assert response.status_code == 403
        assert "disabled" in response.json()["detail"].casefold()
    finally:
        _clear_bootstrap_env()
        reset_runtime()


def test_bootstrap_dev_blocked_when_cf_env_production() -> None:
    os.environ.pop("CF_AUTH_REQUIRED", None)
    _clear_bootstrap_env()
    os.environ["CF_BOOTSTRAP_DEV_TENANT"] = "1"
    os.environ["CF_ENV"] = "production"
    try:
        reset_runtime()
        client = TestClient(app)
        response = client.post("/v1/tenants/bootstrap-dev")
        assert response.status_code == 403
        assert "production" in response.json()["detail"].casefold()
    finally:
        _clear_bootstrap_env()
        reset_runtime()


def test_bootstrap_dev_enabled_with_flag() -> None:
    os.environ.pop("CF_AUTH_REQUIRED", None)
    _clear_bootstrap_env()
    os.environ["CF_BOOTSTRAP_DEV_TENANT"] = "1"
    try:
        reset_runtime()
        client = TestClient(app)
        response = client.post("/v1/tenants/bootstrap-dev")
        assert response.status_code == 200
        payload = response.json()
        assert payload["tenant_id"] == "dev"
        assert payload["api_key"] == "dev-local-key"
        who = client.get(
            "/v1/whoami",
            headers={"Authorization": f"Bearer {payload['api_key']}"},
        )
        assert who.status_code == 200
        assert who.json()["tenant_id"] == "dev"
    finally:
        _clear_bootstrap_env()
        reset_runtime()
