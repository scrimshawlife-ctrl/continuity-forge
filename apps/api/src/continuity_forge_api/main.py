from fastapi import FastAPI
from pydantic import BaseModel

from continuity_forge_compiler import compile_text
from continuity_forge_ir import ScriptDocument

app = FastAPI(title="Continuity Forge API", version="0.1.0")


class CompileRequest(BaseModel):
    title: str = "Untitled"
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compile", response_model=ScriptDocument)
def compile_script(request: CompileRequest) -> ScriptDocument:
    return compile_text(request.text, title=request.title)
