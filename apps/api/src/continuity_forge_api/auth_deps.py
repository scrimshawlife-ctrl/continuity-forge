"""FastAPI auth dependencies for multi-tenant API keys."""

from __future__ import annotations

import os

from continuity_forge_auth import AuthError, AuthService, Principal
from continuity_forge_runtime import get_runtime
from fastapi import Depends, Header, HTTPException


def get_auth_service() -> AuthService:
    return get_runtime().auth


def auth_required() -> bool:
    return os.environ.get("CF_AUTH_REQUIRED", "").casefold() in {"1", "true", "yes"}


def get_principal(
    authorization: str | None = Header(default=None),
    service: AuthService = Depends(get_auth_service),
) -> Principal:
    if not auth_required():
        if authorization:
            try:
                return service.authenticate(authorization)
            except AuthError:
                return Principal(tenant_id="anonymous", actor_id="anonymous", scopes=["*"])
        return Principal(tenant_id="anonymous", actor_id="anonymous", scopes=["*"])
    try:
        return service.authenticate(authorization)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def require_principal(principal: Principal = Depends(get_principal)) -> Principal:
    return principal


def tenant_document_key(tenant_id: str, document_key: str) -> str:
    """Scope document keys per tenant to enforce isolation.

    Uses '::' (not '/') so keys remain single path segments in REST routes.

    Isolation rules:
    - Logical keys (e.g. ``script-1``) become ``{tenant_id}::script-1``.
    - Keys already scoped to *this* tenant are returned unchanged.
    - Keys that look like another tenant's scoped key (contain ``::`` but do
      not start with this tenant's prefix) are re-scoped under the caller's
      tenant, so tenant A can never address tenant B's storage namespace.
    """
    prefix = f"{tenant_id}::"
    if document_key.startswith(prefix):
        return document_key
    return f"{prefix}{document_key}"
