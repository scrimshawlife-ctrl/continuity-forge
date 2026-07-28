from continuity_forge_compiler import compile_text
from continuity_forge_ir import ScriptDocument
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Continuity Forge API", version="0.2.0")


class CompileRequest(BaseModel):
    title: str = "Untitled"
    text: str
    revision: str = "0.1.0"
    document_key: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compile", response_model=ScriptDocument)
def compile_script(request: CompileRequest) -> ScriptDocument:
    return compile_text(
        request.text,
        title=request.title,
        revision=request.revision,
        document_key=request.document_key,
    )
