from typing import Any, Literal
from uuid import UUID

from continuity_forge_auth import Principal, bootstrap_dev_tenant
from continuity_forge_compiler import compile_fdx_text, compile_text
from continuity_forge_harness import (
    PipelineCommand,
    PipelineError,
    WorkflowRun,
    execute_kernel_pipeline,
    temporal_registration_manifest,
)
from continuity_forge_ir import ScriptDocument
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from continuity_forge_operator import (
    ApprovalStatus,
    MutationEnvelope,
    OperatorError,
    ProjectRecord,
    WriteLease,
)
from continuity_forge_providers import ArtifactCandidate
from continuity_forge_repair import LoopResult, run_repair_loop
from continuity_forge_runtime import RuntimeContext, get_runtime
from continuity_forge_shots import ShotContractBundle, compile_shot_contracts
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from continuity_forge_api.auth_deps import require_principal, tenant_document_key

app = FastAPI(title="Continuity Forge API", version="1.1.0")


def _rt() -> RuntimeContext:
    return get_runtime()


class CompileRequest(BaseModel):
    title: str = "Untitled"
    text: str
    revision: str = "0.1.0"
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"


class LeaseRequest(BaseModel):
    document_key: str
    holder: str
    scope: str = "project"
    ttl_seconds: int = 300


class IngestRequest(BaseModel):
    document_key: str
    title: str = "Untitled"
    text: str
    revision: str = "0.1.0"
    format: Literal["fountain", "fdx"] = "fountain"
    actor_id: str
    authorization_scope: str = "kernel:pipeline"
    idempotency_key: str
    rationale: str
    expected_state_hash: str | None = None


class ApprovalRequest(BaseModel):
    document_key: str
    kind: str
    actor_id: str
    authorization_scope: str = "approvals"
    idempotency_key: str
    rationale: str
    target_ref: str | None = None


class ApprovalDecision(BaseModel):
    approval_id: UUID
    status: Literal["granted", "denied"]
    actor_id: str
    authorization_scope: str = "approvals"
    idempotency_key: str
    rationale: str


class GenerateRequest(BaseModel):
    document_key: str
    shot_id: str
    seed: str = "0"
    actor_id: str
    authorization_scope: str = "generation:preview"
    idempotency_key: str
    rationale: str = "preview generation"


class RepairLoopRequest(BaseModel):
    document_key: str
    shot_id: str
    seed: str = "0"
    max_attempts: int = 3
    fail_first: bool = False
    actor_id: str
    authorization_scope: str = "generation:repair"
    idempotency_key: str
    rationale: str = "repair loop"


def _document(request: CompileRequest) -> ScriptDocument:
    compiler = compile_fdx_text if request.format == "fdx" else compile_text
    return compiler(
        request.text,
        title=request.title,
        revision=request.revision,
        document_key=request.document_key,
    )


def _shot(document_key: str, shot_id: str) -> dict[str, Any]:
    project = _rt().project_store.get_project(document_key)
    if project is None or not project.shot_contracts:
        raise HTTPException(status_code=404, detail="project or shot contracts not found")
    contracts = project.shot_contracts.get("contracts") or []
    for contract in contracts:
        if not isinstance(contract, dict):
            continue
        if str(contract.get("shot_id")) == shot_id:
            return {str(k): v for k, v in contract.items()}
    raise HTTPException(status_code=404, detail="shot not found")


def _store_candidate(candidate: ArtifactCandidate) -> str | None:
    sink = _rt().artifact_store
    if sink is None:
        return None
    return sink.put(candidate)


@app.get("/health")
def health() -> dict[str, str]:
    rt = _rt()
    return {"status": "ok", "backend": rt.backend, "version": "1.1.0"}


@app.get("/v1/whoami")
def whoami(principal: Principal = Depends(require_principal)) -> dict[str, Any]:
    return principal.model_dump(mode="json")


@app.post("/v1/tenants/bootstrap-dev")
def bootstrap_dev() -> dict[str, str]:
    """Create/reset the local dev tenant and return its API key (dev only)."""
    rt = _rt()
    tenant, key = bootstrap_dev_tenant(rt.auth)
    return {"tenant_id": tenant.tenant_id, "api_key": key}


@app.post("/v1/compile", response_model=ScriptDocument)
def compile_script(request: CompileRequest) -> ScriptDocument:
    return _document(request)


@app.post("/v1/continuity-ledger", response_model=ContinuityLedger)
def continuity_ledger(request: CompileRequest) -> ContinuityLedger:
    return build_continuity_ledger(_document(request))


@app.post("/v1/shot-contracts", response_model=ShotContractBundle)
def shot_contracts(request: CompileRequest) -> ShotContractBundle:
    return compile_shot_contracts(_document(request))


@app.post("/v1/pipeline/runs", response_model=WorkflowRun)
def start_pipeline_run(command: PipelineCommand) -> WorkflowRun:
    try:
        return execute_kernel_pipeline(command, store=_rt().run_store)
    except PipelineError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/v1/pipeline/runs/{run_id}", response_model=WorkflowRun)
def get_pipeline_run(run_id: UUID) -> WorkflowRun:
    run = _rt().run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="pipeline run not found")
    return run


@app.get("/v1/pipeline/temporal-manifest")
def pipeline_temporal_manifest() -> dict[str, object]:
    return temporal_registration_manifest()


@app.post("/v1/projects/lease", response_model=WriteLease)
def acquire_lease(
    request: LeaseRequest,
    principal: Principal = Depends(require_principal),
) -> WriteLease:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    try:
        return _rt().project_store.acquire_lease(
            key,
            request.holder or principal.actor_id,
            scope=request.scope,
            ttl_seconds=request.ttl_seconds,
        )
    except OperatorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/v1/projects/{document_key}/lease")
def release_lease(
    document_key: str,
    holder: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, str]:
    key = tenant_document_key(principal.tenant_id, document_key)
    try:
        _rt().project_store.release_lease(key, holder)
    except OperatorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "released"}


@app.post("/v1/projects/ingest")
def ingest_project(
    request: IngestRequest,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    envelope = MutationEnvelope(
        actor_id=request.actor_id or principal.actor_id,
        authorization_scope=request.authorization_scope,
        idempotency_key=request.idempotency_key,
        rationale=request.rationale,
        expected_state_hash=request.expected_state_hash,
    )
    try:
        project, run = _rt().project_store.ingest_script(
            document_key=key,
            title=request.title,
            text=request.text,
            revision=request.revision,
            format=request.format,
            envelope=envelope,
        )
    except (OperatorError, PipelineError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "tenant_id": principal.tenant_id,
        "project": project.model_dump(mode="json"),
        "run": run.model_dump(mode="json"),
    }


@app.get("/v1/projects/{document_key}", response_model=ProjectRecord)
def get_project(
    document_key: str,
    principal: Principal = Depends(require_principal),
) -> ProjectRecord:
    key = tenant_document_key(principal.tenant_id, document_key)
    project = _rt().project_store.get_project(key)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@app.get("/v1/projects/{document_key}/status")
def project_status(
    document_key: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, document_key)
    payload = _rt().project_store.resource(f"cf://projects/{key}/status")
    if payload is None:
        raise HTTPException(status_code=404, detail="project not found")
    result = {str(k): v for k, v in payload.items()}
    result["tenant_id"] = principal.tenant_id
    return result


@app.get("/v1/resources")
def get_resource(uri: str) -> dict[str, Any]:
    payload = _rt().project_store.resource(uri)
    if payload is None:
        raise HTTPException(status_code=404, detail="resource not found")
    return {str(k): v for k, v in payload.items()}


@app.post("/v1/approvals/request")
def request_approval(
    request: ApprovalRequest,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    envelope = MutationEnvelope(
        actor_id=request.actor_id or principal.actor_id,
        authorization_scope=request.authorization_scope,
        idempotency_key=request.idempotency_key,
        rationale=request.rationale,
    )
    try:
        record = _rt().project_store.request_approval(
            document_key=key,
            kind=request.kind,
            envelope=envelope,
            target_ref=request.target_ref,
        )
    except OperatorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/v1/approvals/decide")
def decide_approval(
    request: ApprovalDecision,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    envelope = MutationEnvelope(
        actor_id=request.actor_id or principal.actor_id,
        authorization_scope=request.authorization_scope,
        idempotency_key=request.idempotency_key,
        rationale=request.rationale,
    )
    try:
        record = _rt().project_store.record_approval(
            approval_id_value=request.approval_id,
            status=ApprovalStatus(request.status),
            envelope=envelope,
        )
    except OperatorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@app.post("/v1/generate/preview", response_model=ArtifactCandidate)
def generate_preview(
    request: GenerateRequest,
    principal: Principal = Depends(require_principal),
) -> ArtifactCandidate:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    contract = _shot(key, request.shot_id)
    candidate = _rt().gateway.generate_for_shot(contract, seed=request.seed)
    _store_candidate(candidate)
    return candidate


@app.post("/v1/generate/repair-loop", response_model=LoopResult)
def generate_repair_loop(
    request: RepairLoopRequest,
    principal: Principal = Depends(require_principal),
) -> LoopResult:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    contract = _shot(key, request.shot_id)
    result = run_repair_loop(
        contract,
        gateway=_rt().gateway,
        seed=request.seed,
        max_attempts=request.max_attempts,
        fail_first=request.fail_first,
    )
    if result.accepted_candidate is not None:
        _store_candidate(result.accepted_candidate)
    return result
