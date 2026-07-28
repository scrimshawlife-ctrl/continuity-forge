from __future__ import annotations

from hashlib import sha256
from typing import Annotated

from pydantic import BaseModel, Field


class Tenant(BaseModel):
    tenant_id: Annotated[str, Field(min_length=1)]
    name: str
    api_key_hashes: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=lambda: ["kernel:pipeline", "generation:preview"])


class Principal(BaseModel):
    tenant_id: str
    actor_id: str
    scopes: list[str]


def hash_api_key(raw_key: str) -> str:
    return sha256(raw_key.encode("utf-8")).hexdigest()
