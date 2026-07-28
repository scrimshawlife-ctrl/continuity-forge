import pytest
from continuity_forge_api.auth_deps import tenant_document_key
from continuity_forge_auth import (
    AuthError,
    AuthService,
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
