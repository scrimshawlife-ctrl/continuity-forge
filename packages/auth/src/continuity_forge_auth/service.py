"""Multi-tenant API-key auth service (in-memory / file-backed)."""

from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from .models import Principal, Tenant, hash_api_key


class AuthError(RuntimeError):
    pass


class AuthService:
    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        self._key_index: dict[str, str] = {}  # key_hash -> tenant_id
        self._lock = RLock()

    def upsert_tenant(self, tenant: Tenant) -> Tenant:
        with self._lock:
            # Drop old key index entries for this tenant.
            self._key_index = {
                h: tid for h, tid in self._key_index.items() if tid != tenant.tenant_id
            }
            self._tenants[tenant.tenant_id] = tenant
            for key_hash in tenant.api_key_hashes:
                self._key_index[key_hash] = tenant.tenant_id
            return tenant.model_copy(deep=True)

    def register_api_key(self, tenant_id: str, raw_key: str) -> Tenant:
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if tenant is None:
                raise AuthError(f"unknown tenant: {tenant_id}")
            digest = hash_api_key(raw_key)
            hashes = list(dict.fromkeys([*tenant.api_key_hashes, digest]))
            updated = tenant.model_copy(update={"api_key_hashes": hashes})
            return self.upsert_tenant(updated)

    def authenticate(self, bearer_token: str | None) -> Principal:
        if not bearer_token:
            raise AuthError("missing bearer token")
        token = bearer_token.removeprefix("Bearer ").strip()
        if not token:
            raise AuthError("empty bearer token")
        digest = hash_api_key(token)
        with self._lock:
            tenant_id = self._key_index.get(digest)
            if tenant_id is None:
                raise AuthError("invalid API key")
            tenant = self._tenants[tenant_id]
            return Principal(
                tenant_id=tenant.tenant_id,
                actor_id=f"api-key:{digest[:12]}",
                scopes=list(tenant.scopes),
            )

    def require_scope(self, principal: Principal, scope: str) -> None:
        if scope not in principal.scopes and "*" not in principal.scopes:
            raise AuthError(f"principal lacks scope: {scope}")

    def list_tenants(self) -> list[Tenant]:
        with self._lock:
            return [t.model_copy(deep=True) for t in self._tenants.values()]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"tenants": [t.model_dump(mode="json") for t in self.list_tenants()]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("tenants", []):
            self.upsert_tenant(Tenant.model_validate(raw))


DEFAULT_AUTH_SERVICE = AuthService()


def bootstrap_dev_tenant(
    service: AuthService | None = None,
    *,
    tenant_id: str = "dev",
    api_key: str = "dev-local-key",
) -> tuple[Tenant, str]:
    """Create a development tenant + raw API key (returned once)."""
    active = service or DEFAULT_AUTH_SERVICE
    tenant = Tenant(tenant_id=tenant_id, name="Development", api_key_hashes=[hash_api_key(api_key)])
    active.upsert_tenant(tenant)
    return tenant, api_key
