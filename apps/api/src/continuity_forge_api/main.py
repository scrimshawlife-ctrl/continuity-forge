from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from continuity_forge_compiler import compile_fdx_result, compile_text_result
from continuity_forge_ir import CompileResult

app = FastAPI(title="Continuity Forge API", version="0.2.0")


class CompileRequest(BaseModel):
    title: str = "Untitled"
    text: str
    source_format: Literal["fountain", "fdx"] = "fountain"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compile", response_model=CompileResult)
def compile_script(request: CompileRequest) -> CompileResult:
    if request.source_format == "fdx":
        return compile_fdx_result(request.text, title=request.title)
    return compile_text_result(request.text, title=request.title)
