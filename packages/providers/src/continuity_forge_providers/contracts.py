from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class ModelRequest(BaseModel):
    task: str
    input: dict[str, Any]
    schema_name: str | None = None


class ModelResult(BaseModel):
    provider: str
    model: str
    output: dict[str, Any]
    authority: str = "PROPOSED"


class ModelGateway(Protocol):
    async def execute(self, request: ModelRequest) -> ModelResult: ...
