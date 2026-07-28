import os

import pytest
from continuity_forge_api.auth_deps import tenant_document_key
from continuity_forge_auth import (
    AuthError,
    AuthService,
    bootstrap_dev_allowed,
    bootstrap_dev_tenant,
    hash_api_key,
)


def test_api_key_auth_and_tenant_isolation_keys() -> None:
    service = AuthService()
    tenant, raw = bootstrap_dev_tenant(service, tenant_id="acme", api_key="secret-acme")
    assert hash_api_key(raw) in tenant.api_key_hashes
    principal = service.authenticate(f"Bearer {raw}")
    assert principal.tenant_id == "acme"
    assert tenant_document_key(principal.tenant_id, "script-1") == "acme::script-1"
    assert tenant_document_key("acme", "acme::script-1") == "acme::script-1"


def test_tenant_document_key_cannot_address_foreign_tenant() -> None:
    """Tenant A keys never resolve into tenant B's storage namespace."""
    a_key = tenant_document_key("tenant-a", "shared-doc")
    b_key = tenant_document_key("tenant-b", "shared-doc")
    assert a_key == "tenant-a::shared-doc"
    assert b_key == "tenant-b::shared-doc"
    assert a_key != b_key

    # Attempt to pass the other tenant's fully-scoped key: re-scoped under caller.
    spoofed = tenant_document_key("tenant-b", "tenant-a::shared-doc")
    assert spoofed == "tenant-b::tenant-a::shared-doc"
    assert spoofed != a_key
    assert spoofed.startswith("tenant-b::")

    # Own-prefix keys stay stable (idempotent scoping).
    assert tenant_document_key("tenant-a", a_key) == a_key


def test_invalid_key_rejected() -> None:
    service = AuthService()
    bootstrap_dev_tenant(service, tenant_id="t", api_key="good")
    with pytest.raises(AuthError, match="invalid API key"):
        service.authenticate("Bearer bad")


def test_scope_enforcement() -> None:
    service = AuthService()
    bootstrap_dev_tenant(service, tenant_id="t2", api_key="k2")
    principal = service.authenticate("Bearer k2")
    service.require_scope(principal, "kernel:pipeline")
    with pytest.raises(AuthError, match="lacks scope"):
        service.require_scope(principal, "admin:*")


def test_bootstrap_dev_allowed_requires_flag() -> None:
    saved = {
        "CF_BOOTSTRAP_DEV_TENANT": os.environ.get("CF_BOOTSTRAP_DEV_TENANT"),
        "CF_ENV": os.environ.get("CF_ENV"),
        "ENVIRONMENT": os.environ.get("ENVIRONMENT"),
    }
    try:
        os.environ.pop("CF_BOOTSTRAP_DEV_TENANT", None)
        os.environ.pop("CF_ENV", None)
        os.environ.pop("ENVIRONMENT", None)
        assert bootstrap_dev_allowed() is False

        os.environ["CF_BOOTSTRAP_DEV_TENANT"] = "1"
        assert bootstrap_dev_allowed() is True

        os.environ["CF_ENV"] = "production"
        assert bootstrap_dev_allowed() is False

        os.environ["CF_ENV"] = "prod"
        assert bootstrap_dev_allowed() is False

        os.environ["CF_ENV"] = "development"
        assert bootstrap_dev_allowed() is True

        os.environ.pop("CF_ENV", None)
        os.environ["ENVIRONMENT"] = "production"
        assert bootstrap_dev_allowed() is False
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
