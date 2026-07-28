from typing import Literal
from uuid import UUID

from continuity_forge_compiler import compile_fdx_text, compile_text
from continuity_forge_harness import (
    DEFAULT_RUN_STORE,
    PipelineCommand,
    PipelineError,
    WorkflowRun,
    execute_kernel_pipeline,
    temporal_registration_manifest,
)
from continuity_forge_ir import ScriptDocument
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from continuity_forge_shots import ShotContractBundle, compile_shot_contracts
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Continuity Forge API", version="0.5.0")


class CompileRequest(BaseModel):
    title: str = "Untitled"
    text: str
    revision: str = "0.1.0"
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"


def _document(request: CompileRequest) -> ScriptDocument:
    compiler = compile_fdx_text if request.format == "fdx" else compile_text
    return compiler(
        request.text,
        title=request.title,
        revision=request.revision,
        document_key=request.document_key,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/compile", response_model=ScriptDocument)
def compile_script(request: CompileRequest) -> ScriptDocument:
    return _document(request)


@app.post("/v1/continuity-ledger", response_model=ContinuityLedger)
def continuity_ledger(request: CompileRequest) -> ContinuityLedger:
    """Compile source and derive a deterministic continuity ledger (read-only)."""
    return build_continuity_ledger(_document(request))


@app.post("/v1/shot-contracts", response_model=ShotContractBundle)
def shot_contracts(request: CompileRequest) -> ShotContractBundle:
    """Compile source into model-neutral shot contracts (read-only)."""
    document = _document(request)
    return compile_shot_contracts(document)


@app.post("/v1/pipeline/runs", response_model=WorkflowRun)
def start_pipeline_run(command: PipelineCommand) -> WorkflowRun:
    """Execute the durable kernel pipeline (compile → ledger → shots)."""
    try:
        return execute_kernel_pipeline(command, store=DEFAULT_RUN_STORE)
    except PipelineError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/pipeline/runs/{run_id}", response_model=WorkflowRun)
def get_pipeline_run(run_id: UUID) -> WorkflowRun:
    run = DEFAULT_RUN_STORE.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="pipeline run not found")
    return run


@app.get("/v1/pipeline/temporal-manifest")
def pipeline_temporal_manifest() -> dict[str, object]:
    """Return Temporal adapter registration contracts for worker bootstrap."""
    return temporal_registration_manifest()
