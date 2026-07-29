from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from continuity_forge_auth import Principal, bootstrap_dev_allowed, bootstrap_dev_tenant
from continuity_forge_compiler import (
    compile_fdx_text,
    compile_incremental,
    compile_text,
)
from continuity_forge_harness import (
    PipelineCommand,
    PipelineError,
    WorkflowRun,
    build_event_page,
    execute_kernel_pipeline,
    temporal_registration_manifest,
)
from continuity_forge_ir import ChangeSet, ScriptDocument, StaleReport
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from continuity_forge_operator import (
    ApprovalStatus,
    MutationEnvelope,
    OperatorError,
    ProjectRecord,
    WriteLease,
    apply_operator_override,
    build_analysis_summary,
    build_entity_profiles,
    build_scene_cards,
    build_scene_detail,
    detect_script_format,
    friendly_parser_error,
    generate_document_key,
    make_review_decision,
    package_is_provider_neutral,
    prepare_scene_package,
    resolve_conflict,
)
from continuity_forge_operator.product_workflow import OperatorOverride
from continuity_forge_providers import ArtifactCandidate
from continuity_forge_repair import LoopResult, ProofReceipt, run_controlled_proof, run_repair_loop
from continuity_forge_runtime import RuntimeContext, get_runtime
from continuity_forge_shots import (
    BreakdownPackage,
    ShotContractBundle,
    breakdown_to_markdown,
    build_breakdown_from_text,
    compile_shot_contracts,
    preview_invalidation,
)
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from continuity_forge_api.auth_deps import require_principal, tenant_document_key

API_VERSION = "1.5.3"
app = FastAPI(title="Continuity Forge API", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


class ProofRequest(BaseModel):
    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    seed: str = "proof"
    budget_seconds: float = Field(default=60.0, ge=1.0, le=600.0)
    actor_id: str = "proof-operator"


class InvalidationPreviewRequest(BaseModel):
    """Pure invalidation preview — does not write canon or elevate PROPOSED."""

    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    revision: str = "0.1.0"
    change: ChangeSet = Field(default_factory=ChangeSet)
    force_full: bool = False


class IncrementalCompileRequest(BaseModel):
    """Optional incremental compile (full validation + prior reconcile + invalidation)."""

    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    revision: str = "0.1.0"
    # Prior Production IR JSON (optional). When omitted, behaves like full compile + recompiled tags.
    prior_document: dict[str, Any] | None = None
    force_full_invalidation: bool = False


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
    return {"status": "ok", "backend": rt.backend, "version": API_VERSION}


@app.get("/v1/whoami")
def whoami(principal: Principal = Depends(require_principal)) -> dict[str, Any]:
    return principal.model_dump(mode="json")


@app.post("/v1/tenants/bootstrap-dev")
def bootstrap_dev() -> dict[str, str]:
    """Create/reset the local dev tenant and return its API key (dev only).

    Disabled unless ``CF_BOOTSTRAP_DEV_TENANT`` is truthy, and always disabled
    when ``CF_ENV``/``ENVIRONMENT`` is ``production``/``prod``.
    """
    if not bootstrap_dev_allowed():
        raise HTTPException(
            status_code=403,
            detail=(
                "bootstrap-dev is disabled: set CF_BOOTSTRAP_DEV_TENANT=1 for local "
                "development only; never enable in production (also blocked when "
                "CF_ENV/ENVIRONMENT is production|prod)"
            ),
        )
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


@app.post("/v1/breakdown", response_model=BreakdownPackage)
def breakdown_endpoint(request: CompileRequest) -> BreakdownPackage:
    """Paste/import screenplay → shot-by-shot breakdown with continuity.

    Machine-readable handoff package for connectors and export.
    Read-side only; not production film; no PROPOSED media elevation.
    """
    return build_breakdown_from_text(
        request.text,
        title=request.title,
        document_key=request.document_key,
        format=request.format,
        revision=request.revision,
    )


@app.post("/v1/breakdown/markdown")
def breakdown_markdown_endpoint(request: CompileRequest) -> dict[str, Any]:
    """Same breakdown as POST /v1/breakdown, returned as Markdown text."""
    package = build_breakdown_from_text(
        request.text,
        title=request.title,
        document_key=request.document_key,
        format=request.format,
        revision=request.revision,
    )
    return {
        "schema_version": package.schema_version,
        "claim": package.claim,
        "package_hash": package.package_hash,
        "markdown": breakdown_to_markdown(package),
        "shot_count": package.shot_count,
        "scene_count": package.scene_count,
        "entity_count": package.entity_count,
    }


@app.post("/v1/compile/incremental")
def compile_incremental_endpoint(request: IncrementalCompileRequest) -> dict[str, Any]:
    """Full schema-validated compile with optional prior-IR ID reconcile + invalidation.

    Default short-path remains ``POST /v1/compile``. This endpoint is optional for
    edit loops. Read-side only: does not ingest project canon or elevate PROPOSED.
    """
    prior = None
    if request.prior_document is not None:
        prior = ScriptDocument.model_validate(request.prior_document)
    result = compile_incremental(
        request.text,
        title=request.title,
        revision=request.revision,
        document_key=request.document_key,
        format=request.format,
        prior=prior,
        force_full_invalidation=request.force_full_invalidation,
    )
    return result.model_dump(mode="json")


@app.post("/v1/invalidation/preview")
def invalidation_preview(request: InvalidationPreviewRequest) -> dict[str, Any]:
    """Return deterministic stale artifact set for a change (read-only).

    Does not mutate project stores, leases, or provider state. PROPOSED
    candidates are never elevated to canon by this endpoint.
    """
    document = _document(
        CompileRequest(
            title=request.title,
            text=request.text,
            document_key=request.document_key,
            format=request.format,
            revision=request.revision,
        )
    )
    bundle = compile_shot_contracts(document)
    report: StaleReport = preview_invalidation(
        document,
        bundle,
        request.change,
        force_full=request.force_full,
    )
    from continuity_forge_ir import stale_shot_ids

    return {
        "report": report.model_dump(mode="json"),
        "stale_shot_ids": stale_shot_ids(report),
        "scene_count": len(document.scenes),
        "shot_count": len(bundle.contracts),
        "claim": "invalidation_preview_not_a_canon_write",
    }


@app.post("/v1/pipeline/runs", response_model=WorkflowRun)
def start_pipeline_run(command: PipelineCommand) -> WorkflowRun:
    # Validate shared write-contract fields via MutationEnvelope (universal gate).
    # PipelineCommand keeps its own command_schema_version and shot_contracts
    # expected_state_hash domain.
    MutationEnvelope.from_parts(
        actor_id=command.actor_id,
        authorization_scope=command.authorization_scope,
        idempotency_key=command.idempotency_key,
        rationale=command.rationale,
        expected_state_hash=command.expected_state_hash,
    )
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


@app.get("/v1/pipeline/runs/{run_id}/events")
def get_pipeline_run_events(
    run_id: UUID,
    after: int = 0,
    last_event_id: str | None = None,
) -> dict[str, Any]:
    """Poll workflow events for a run (observability; not film canon).

    Transport is **poll-first**. Clients resume with ``after`` (sequence) or
    ``last_event_id`` without replaying mutations. SSE may be added later.

    Explicit: workflow complete ≠ production ready.
    """
    run = _rt().run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="pipeline run not found")
    page = build_event_page(
        run,
        after_sequence=max(0, after),
        last_event_id=last_event_id,
    )
    return page.model_dump(mode="json")


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


@app.get("/v1/projects/{document_key}/lease")
def get_lease(
    document_key: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, document_key)
    lease = _rt().project_store.get_lease(key)
    if lease is None:
        return {"document_key": key, "active": False, "lease": None}
    return {
        "document_key": key,
        "active": lease.is_active(),
        "lease": lease.model_dump(mode="json"),
    }


@app.delete("/v1/projects/{document_key}/lease")
def release_lease(
    document_key: str,
    holder: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, str]:
    key = tenant_document_key(principal.tenant_id, document_key)
    try:
        _rt().project_store.release_lease(key, holder or principal.actor_id)
    except OperatorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "released"}


@app.post("/v1/projects/ingest")
def ingest_project(
    request: IngestRequest,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, request.document_key)
    envelope = MutationEnvelope.from_parts(
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


def _project_summary(project: ProjectRecord) -> dict[str, Any]:
    return {
        "document_key": project.document_key,
        "title": project.title,
        "revision": project.revision,
        "format": project.format,
        "source_hash": project.source_hash,
        "state_hash": project.state_hash,
        "last_pipeline_run_id": (
            str(project.last_pipeline_run_id) if project.last_pipeline_run_id else None
        ),
        "scene_count": len((project.production_ir or {}).get("scenes") or []),
        "shot_count": len((project.shot_contracts or {}).get("contracts") or []),
    }


@app.get("/v1/projects")
def list_projects(
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """List projects for the authenticated tenant (keys scoped as tenant::doc)."""
    prefix = f"{principal.tenant_id}::"
    projects = [
        _project_summary(p)
        for p in _rt().project_store.list_projects()
        if p.document_key.startswith(prefix)
    ]
    projects.sort(key=lambda row: str(row["document_key"]))
    return {"tenant_id": principal.tenant_id, "projects": projects}


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


@app.get("/v1/projects/{document_key}/approvals")
def list_project_approvals(
    document_key: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, document_key)
    records = _rt().project_store.list_approvals(key)
    return {
        "document_key": key,
        "approvals": [r.model_dump(mode="json") for r in records],
    }


@app.get("/v1/projects/{document_key}/runs")
def list_project_runs(
    document_key: str,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    key = tenant_document_key(principal.tenant_id, document_key)
    runs = _rt().project_store.list_runs_for_project(key)
    return {
        "document_key": key,
        "runs": [r.model_dump(mode="json") for r in runs],
    }


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
    envelope = MutationEnvelope.from_parts(
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
    envelope = MutationEnvelope.from_parts(
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
    # PROPOSED-only: validate write-contract fields for audit, no canon write.
    MutationEnvelope.from_parts(
        actor_id=request.actor_id or principal.actor_id,
        authorization_scope=request.authorization_scope,
        idempotency_key=request.idempotency_key,
        rationale=request.rationale,
    )
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
    # PROPOSED-only: validate write-contract fields for audit, no canon write.
    MutationEnvelope.from_parts(
        actor_id=request.actor_id or principal.actor_id,
        authorization_scope=request.authorization_scope,
        idempotency_key=request.idempotency_key,
        rationale=request.rationale,
    )
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


@app.post("/v1/proof", response_model=ProofReceipt)
def controlled_proof(
    request: ProofRequest,
    principal: Principal = Depends(require_principal),
) -> ProofReceipt:
    """Run controlled proof (mock media). Receipt claims not production-ready."""
    raw_key = request.document_key or request.title.lower().replace(" ", "-") or "document"
    key = tenant_document_key(principal.tenant_id, raw_key)
    try:
        receipt = run_controlled_proof(
            text=request.text,
            title=request.title,
            format=request.format,
            store=_rt().project_store,
            gateway=_rt().gateway,
            document_key=key,
            actor_id=request.actor_id or principal.actor_id,
            seed=request.seed,
            budget_seconds=request.budget_seconds,
        )
    except (OperatorError, PipelineError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return receipt


# --- Product workflow adapters (view models; do not replace kernel contracts) -


class ProductAnalyzeRequest(BaseModel):
    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    revision: str = "0.1.0"
    production_type: str | None = None
    resolved_conflict_ids: list[str] = Field(default_factory=list)
    overrides: list[dict[str, Any]] = Field(default_factory=list)


class ProductCreateProjectRequest(BaseModel):
    title: str = Field(min_length=1)
    production_type: str = "Other"
    text: str = ""
    format: Literal["fountain", "fdx"] | None = None
    filename: str | None = None
    document_key: str | None = None
    actor_id: str = "product-ui"
    persist: bool = True


class ProductPrepareSceneRequest(BaseModel):
    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    revision: str = "0.1.0"
    scene_id: str
    warnings_acknowledged: bool = False
    resolved_conflict_ids: list[str] = Field(default_factory=list)
    overrides: list[dict[str, Any]] = Field(default_factory=list)


class ProductOverrideRequest(BaseModel):
    title: str = "Untitled"
    text: str
    document_key: str | None = None
    format: Literal["fountain", "fdx"] = "fountain"
    revision: str = "0.1.0"
    target_kind: str
    target_id: str
    field_name: str
    original_value: str
    locked_value: str
    rationale: str = ""
    confirm: bool = False
    existing_overrides: list[dict[str, Any]] = Field(default_factory=list)


class ProductResolveConflictRequest(BaseModel):
    conflict: dict[str, Any]
    choice_id: str
    document_key: str | None = None


class ProductReviewDecisionRequest(BaseModel):
    shot_id: str
    action: Literal["accept", "accept_with_note", "repair", "regenerate", "reject"]
    candidate_id: str | None = None
    note: str = ""
    actor_id: str = "operator"
    document_key: str | None = None


def _parse_overrides(raw: list[dict[str, Any]]) -> list[OperatorOverride]:
    out: list[OperatorOverride] = []
    for item in raw:
        try:
            out.append(OperatorOverride.model_validate(item))
        except Exception as exc:  # noqa: BLE001 — skip malformed overlay entries
            _ = exc
            continue
    return out


def _product_store_key(document_key: str | None, tenant_id: str = "anonymous") -> str | None:
    if not document_key:
        return None
    if "::" in document_key:
        return document_key
    return tenant_document_key(tenant_id, document_key)


def _meta_list(meta: dict[str, object], key: str) -> list[Any]:
    raw = meta.get(key)
    if isinstance(raw, list):
        return list(raw)
    return []


@app.post("/v1/product/create-project")
def product_create_project(
    request: ProductCreateProjectRequest,
    principal: Principal = Depends(require_principal),
) -> dict[str, Any]:
    """Create a durable project via ProjectStore when script text is present.

    Uses MutationEnvelope + ingest_script(require_lease=False). Product meta
    (production_type, phase) is stored on the same runtime store overlay.
    """
    key_raw = request.document_key or generate_document_key(request.title)
    key = tenant_document_key(principal.tenant_id, key_raw)
    fmt = request.format
    if fmt is None and request.text:
        fmt = detect_script_format(request.filename, request.text)
    if fmt is None:
        fmt = "fountain"
    phase = "IMPORTED" if request.text.strip() else "EMPTY"
    project_dump: dict[str, Any] | None = None
    if request.persist and request.text.strip():
        envelope = MutationEnvelope.from_parts(
            actor_id=request.actor_id or principal.actor_id,
            authorization_scope="product.create",
            idempotency_key=f"product-create-{key}-{content_hash_safe(request.text)}",
            rationale="Product UI project create / import",
        )
        try:
            project, _run = _rt().project_store.ingest_script(
                document_key=key,
                title=request.title.strip(),
                text=request.text,
                revision="0.1.0",
                format=fmt,
                envelope=envelope,
                require_lease=False,
            )
            project_dump = project.model_dump(mode="json")
            phase = "IMPORTED"
        except (OperatorError, PipelineError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    meta = _rt().project_store.put_product_meta(
        key,
        {
            "production_type": request.production_type,
            "phase": phase,
            "title": request.title.strip(),
            "format": fmt,
            "document_key": key_raw,
            "tenant_document_key": key,
            "overrides": [],
            "resolved_conflict_ids": [],
            "review_decisions": [],
        },
    )
    return {
        "document_key": key_raw,
        "tenant_document_key": key,
        "title": request.title.strip(),
        "production_type": request.production_type,
        "format": fmt,
        "phase": phase,
        "persisted": project_dump is not None,
        "project": project_dump,
        "product_meta": meta,
        "supported_inputs": [".fountain", ".fdx", ".txt"],
    }


def content_hash_safe(text: str) -> str:
    from continuity_forge_ir import content_hash

    return content_hash(text)[:16]


@app.post("/v1/product/analyze")
def product_analyze(request: ProductAnalyzeRequest) -> dict[str, Any]:
    """Analyze script → creative-language summary + scene cards + continuity profiles.

    Wraps stable ``build_breakdown_from_text``; does not change ``cf.breakdown.v1``.
    """
    if not request.text.strip():
        err = friendly_parser_error("empty script")
        raise HTTPException(status_code=400, detail=err.model_dump(mode="json"))
    try:
        package = build_breakdown_from_text(
            request.text,
            title=request.title,
            document_key=request.document_key,
            format=request.format,
            revision=request.revision,
        )
    except Exception as exc:
        err = friendly_parser_error(exc)
        raise HTTPException(status_code=400, detail=err.model_dump(mode="json")) from exc

    resolved = set(request.resolved_conflict_ids)
    overrides = _parse_overrides(request.overrides)
    # Merge durable meta overrides when document_key present
    store_key = _product_store_key(request.document_key)
    if store_key:
        meta = _rt().project_store.get_product_meta(store_key)
        if meta:
            overrides = _parse_overrides(_meta_list(meta, "overrides")) + overrides
    summary = build_analysis_summary(
        package,
        production_type=request.production_type,
        resolved_conflict_ids=resolved,
    )
    scenes = build_scene_cards(package, conflicts=summary.conflicts, overrides=overrides)
    entities = build_entity_profiles(package, overrides=overrides)
    return {
        "summary": summary.model_dump(mode="json"),
        "scenes": [s.model_dump(mode="json") for s in scenes],
        "entities": [e.model_dump(mode="json") for e in entities],
        "breakdown": package.model_dump(mode="json"),
        "overrides_applied": [o.model_dump(mode="json") for o in overrides],
        "analysis_stages": [
            "Reading screenplay",
            "Detecting scenes",
            "Extracting characters and locations",
            "Building continuity timeline",
            "Preparing shot suggestions",
            "Checking for conflicts",
        ],
    }


@app.post("/v1/product/scenes/{scene_id}")
def product_scene_detail(
    scene_id: str,
    request: ProductAnalyzeRequest,
) -> dict[str, Any]:
    """Scene detail view model (entry/exit, shots as cards, conflicts)."""
    package = build_breakdown_from_text(
        request.text,
        title=request.title,
        document_key=request.document_key,
        format=request.format,
        revision=request.revision,
    )
    overrides = _parse_overrides(request.overrides)
    detail = build_scene_detail(
        package,
        scene_id,
        source_text=request.text,
        resolved_conflict_ids=set(request.resolved_conflict_ids),
        overrides=overrides,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="scene not found")
    return detail.model_dump(mode="json")


@app.post("/v1/product/scenes/{scene_id}/prepare")
def product_prepare_scene(
    scene_id: str,
    request: ProductPrepareSceneRequest,
) -> dict[str, Any]:
    """Compile a provider-neutral Scene Generation Package."""
    if request.scene_id and request.scene_id != scene_id:
        raise HTTPException(status_code=400, detail="scene_id mismatch")
    package = build_breakdown_from_text(
        request.text,
        title=request.title,
        document_key=request.document_key,
        format=request.format,
        revision=request.revision,
    )
    try:
        scene_pkg = prepare_scene_package(
            package,
            scene_id,
            source_text=request.text,
            warnings_acknowledged=request.warnings_acknowledged,
            resolved_conflict_ids=set(request.resolved_conflict_ids),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "package": scene_pkg.model_dump(mode="json"),
        "provider_neutral": package_is_provider_neutral(scene_pkg),
        "export_only": True,
        "providers_configured": False,
        "message": (
            "No generation provider is connected. "
            "You can still export the complete scene and shot packages."
        ),
    }


@app.post("/v1/product/override/preview")
def product_override_preview(request: ProductOverrideRequest) -> dict[str, Any]:
    """Preview or confirm operator override + invalidation.

    When ``confirm=true``, persists USER_LOCKED override on product meta and
    returns profiles with locked values applied. Does not rewrite kernel package.
    """
    package = build_breakdown_from_text(
        request.text,
        title=request.title,
        document_key=request.document_key,
        format=request.format,
        revision=request.revision,
    )
    override, preview = apply_operator_override(
        target_kind=request.target_kind,
        target_id=request.target_id,
        field_name=request.field_name,
        original_value=request.original_value,
        locked_value=request.locked_value,
        package=package,
        rationale=request.rationale,
    )
    all_overrides = _parse_overrides(request.existing_overrides) + [override]
    profiles = build_entity_profiles(package, overrides=all_overrides)
    result: dict[str, Any] = {
        "override": override.model_dump(mode="json"),
        "invalidation": preview.model_dump(mode="json"),
        "requires_confirmation": not request.confirm,
        "entities": [e.model_dump(mode="json") for e in profiles],
        "note": "Override preserves original extracted value; locked value is USER_LOCKED.",
    }
    if request.confirm and request.document_key:
        store_key = _product_store_key(request.document_key) or request.document_key
        meta = _rt().project_store.get_product_meta(store_key) or {}
        prior = _meta_list(meta, "overrides")
        prior.append(override.model_dump(mode="json"))
        stored = _rt().project_store.put_product_meta(
            store_key,
            {
                **meta,
                "overrides": prior,
                "phase": "STALE",
            },
        )
        result["confirmed"] = True
        result["product_meta"] = stored
    return result


@app.post("/v1/product/conflicts/resolve")
def product_resolve_conflict(request: ProductResolveConflictRequest) -> dict[str, Any]:
    """Record an explicit conflict resolution choice (no silent pick)."""
    from continuity_forge_operator.product_workflow import ConflictCard

    try:
        card = ConflictCard.model_validate(request.conflict)
        resolved = resolve_conflict(card, request.choice_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store_key = _product_store_key(request.document_key)
    if store_key:
        meta = _rt().project_store.get_product_meta(store_key) or {}
        ids = _meta_list(meta, "resolved_conflict_ids")
        if resolved.conflict_id not in ids:
            ids.append(resolved.conflict_id)
        _rt().project_store.put_product_meta(store_key, {**meta, "resolved_conflict_ids": ids})
    return {"conflict": resolved.model_dump(mode="json")}


@app.post("/v1/product/review/decision")
def product_review_decision(request: ProductReviewDecisionRequest) -> dict[str, Any]:
    """Record accept/repair/regenerate/reject intent with lineage preserved.

    Does not silently mutate canon — acceptance flags intent only.
    Canon advancement requires MutationEnvelope-backed store paths.
    """
    decision = make_review_decision(
        shot_id=request.shot_id,
        action=request.action,
        candidate_id=request.candidate_id,
        note=request.note,
        actor_id=request.actor_id,
    )
    store_key = _product_store_key(request.document_key)
    if store_key:
        meta = _rt().project_store.get_product_meta(store_key) or {}
        decisions = _meta_list(meta, "review_decisions")
        decisions.append(decision.model_dump(mode="json"))
        _rt().project_store.put_product_meta(store_key, {**meta, "review_decisions": decisions})
        # Optional: request approval via validated mutation path when accepting
        if decision.advances_canon:
            try:
                envelope = MutationEnvelope.from_parts(
                    actor_id=request.actor_id,
                    authorization_scope="product.review.accept",
                    idempotency_key=f"review-{decision.decision_id}",
                    rationale=(
                        f"Accept candidate for shot {request.shot_id}: "
                        f"{request.note or 'operator accept'}"
                    ),
                )
                if _rt().project_store.get_project(store_key) is not None:
                    # Lease required by store — acquire briefly for approval path
                    try:
                        _rt().project_store.acquire_lease(
                            store_key, request.actor_id, scope="project", ttl_seconds=60
                        )
                    except OperatorError:
                        pass
                    _rt().project_store.request_approval(
                        document_key=store_key,
                        kind="commit_candidate",
                        envelope=envelope,
                        target_ref=request.shot_id,
                    )
            except OperatorError:
                pass  # approval optional when lease/project missing
    return {
        "decision": decision.model_dump(mode="json"),
        "lineage_preserved": decision.lineage_preserved,
        "advances_canon_via_mutation_envelope": decision.advances_canon,
        "note": (
            "Lineage preserved. Canonical state advances only through validated "
            "mutation paths — not silent model or UI writes."
        ),
    }


def _mount_web_ui() -> None:
    """Serve the Hallmark operator workbench when apps/web is present."""
    # apps/api/src/continuity_forge_api/main.py → apps/web
    web_dir = Path(__file__).resolve().parents[3] / "web"
    if web_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")


_mount_web_ui()
