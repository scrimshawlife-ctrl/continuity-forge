from __future__ import annotations

from typing import Any
from uuid import UUID

from continuity_forge_compiler import compile_fdx_text, compile_incremental, compile_text
from continuity_forge_harness import (
    PipelineCommand,
    PipelineError,
    build_event_page,
    execute_kernel_pipeline,
    temporal_registration_manifest,
)
from continuity_forge_ir import ScriptDocument
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from continuity_forge_operator import (
    MutationEnvelope,
    OperatorError,
)
from continuity_forge_repair import run_repair_loop
from continuity_forge_runtime import RuntimeContext, get_runtime
from continuity_forge_shots import ShotContractBundle, compile_shot_contracts
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Continuity Forge")


def _rt() -> RuntimeContext:
    return get_runtime()


def _compile(
    source: str,
    title: str,
    document_key: str | None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> ScriptDocument:
    compiler = compile_fdx_text if format == "fdx" else compile_text
    return compiler(source, title=title, document_key=document_key, revision=revision)


def _ledger(
    source: str,
    title: str,
    document_key: str | None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> ContinuityLedger:
    return build_continuity_ledger(_compile(source, title, document_key, format, revision))


@mcp.tool()
def compile_script(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> dict[str, Any]:
    """Compile Fountain or Final Draft XML without mutating canonical state.

    Default full compile path. For edit loops with prior-IR reconcile, use
    ``compile_script_incremental`` (optional; still full schema validation).
    """
    return _compile(source, title, document_key, format, revision).model_dump(mode="json")


@mcp.tool()
def compile_script_incremental(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
    prior_document: dict[str, Any] | None = None,
    force_full_invalidation: bool = False,
) -> dict[str, Any]:
    """Optional incremental compile: full validate + prior-ID reconcile + stale preview.

    Read-side only. Does not ingest project canon or elevate PROPOSED media.
    Default short proofs should keep using ``compile_script``.
    """
    prior = None
    if prior_document is not None:
        prior = ScriptDocument.model_validate(prior_document)
    result = compile_incremental(
        source,
        title=title,
        revision=revision,
        document_key=document_key,
        format=format,
        prior=prior,
        force_full_invalidation=force_full_invalidation,
    )
    return result.model_dump(mode="json")


@mcp.tool()
def get_compile_diagnostics(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> list[dict[str, Any]]:
    """Return deterministic diagnostics for screenplay source."""
    document = _compile(source, title, document_key, format, revision)
    return [item.model_dump(mode="json") for item in document.diagnostics]


@mcp.tool()
def list_scenes(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> list[dict[str, Any]]:
    """List compiled scenes and their stable identifiers."""
    document = _compile(source, title, document_key, format, revision)
    return [
        {
            "scene_id": str(scene.scene_id),
            "ordinal": scene.ordinal,
            "slugline": scene.slugline,
            "atom_count": len(scene.atoms),
        }
        for scene in document.scenes
    ]


@mcp.tool()
def get_scene(
    source: str,
    scene_id: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> dict[str, Any] | None:
    """Get one compiled scene by stable identifier."""
    requested = UUID(scene_id)
    document = _compile(source, title, document_key, format, revision)
    return next(
        (scene.model_dump(mode="json") for scene in document.scenes if scene.scene_id == requested),
        None,
    )


@mcp.tool()
def audit_script_coverage(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> dict[str, Any]:
    """Return source-accounting totals and uncovered spans."""
    return _compile(source, title, document_key, format, revision).coverage.model_dump(mode="json")


@mcp.tool()
def build_ledger(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> dict[str, Any]:
    """Build a deterministic continuity ledger from screenplay source (read-only)."""
    return _ledger(source, title, document_key, format, revision).model_dump(mode="json")


@mcp.tool()
def list_entities(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> list[dict[str, Any]]:
    """List continuity entities derived from the compiled screenplay."""
    ledger = _ledger(source, title, document_key, format, revision)
    return [entity.model_dump(mode="json") for entity in ledger.entities]


@mcp.tool()
def list_setup_payoff_links(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> list[dict[str, Any]]:
    """List setup/payoff links derived from the continuity ledger."""
    ledger = _ledger(source, title, document_key, format, revision)
    return [link.model_dump(mode="json") for link in ledger.setup_payoff_links]


def _shots(
    source: str,
    title: str,
    document_key: str | None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> ShotContractBundle:
    document = _compile(source, title, document_key, format, revision)
    return compile_shot_contracts(document)


@mcp.tool()
def build_shot_contracts(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> dict[str, Any]:
    """Compile model-neutral shot contracts from screenplay source (read-only)."""
    return _shots(source, title, document_key, format, revision).model_dump(mode="json")


@mcp.tool()
def list_shot_summaries(
    source: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
) -> list[dict[str, Any]]:
    """List compact shot-contract summaries for each scene."""
    bundle = _shots(source, title, document_key, format, revision)
    return [
        {
            "shot_id": str(contract.shot_id),
            "scene_id": str(contract.scene_id),
            "label": contract.label,
            "slugline": contract.slugline,
            "constraint_count": len(contract.constraints),
            "required_atom_count": len(contract.required_atom_ids),
        }
        for contract in bundle.contracts
    ]


@mcp.tool()
def run_kernel_pipeline(
    source: str,
    actor_id: str,
    authorization_scope: str,
    idempotency_key: str,
    rationale: str,
    title: str = "Untitled",
    document_key: str | None = None,
    format: str = "fountain",
    revision: str = "0.1.0",
    expected_state_hash: str | None = None,
) -> dict[str, Any]:
    """Execute the durable compile → ledger → shots pipeline under a mutation contract."""
    # Universal write contract gate (shared fields). PipelineCommand owns
    # pipeline schema version and shot_contracts_hash expected-state domain.
    MutationEnvelope.from_parts(
        actor_id=actor_id,
        authorization_scope=authorization_scope,
        idempotency_key=idempotency_key,
        rationale=rationale,
        expected_state_hash=expected_state_hash,
    )
    command = PipelineCommand(
        actor_id=actor_id,
        authorization_scope=authorization_scope,
        idempotency_key=idempotency_key,
        rationale=rationale,
        expected_state_hash=expected_state_hash,
        title=title,
        text=source,
        revision=revision,
        document_key=document_key,
        format=format,  # type: ignore[arg-type]
    )
    try:
        run = execute_kernel_pipeline(command, store=_rt().run_store)
    except PipelineError as exc:
        raise ValueError(str(exc)) from exc
    return run.model_dump(mode="json")


@mcp.tool()
def get_pipeline_run(run_id: str) -> dict[str, Any] | None:
    """Fetch a durable pipeline run by ID."""
    run = _rt().run_store.get(UUID(run_id))
    return None if run is None else run.model_dump(mode="json")


@mcp.tool()
def get_pipeline_run_events(
    run_id: str,
    after: int = 0,
    last_event_id: str | None = None,
) -> dict[str, Any] | None:
    """Poll ordered workflow events for a run (observability; not film canon).

    Resume with ``after`` (sequence) or ``last_event_id`` without replaying
    mutations. Explicit: workflow complete ≠ production ready.
    """
    run = _rt().run_store.get(UUID(run_id))
    if run is None:
        return None
    page = build_event_page(
        run,
        after_sequence=max(0, after),
        last_event_id=last_event_id,
    )
    return page.model_dump(mode="json")


@mcp.tool()
def get_temporal_manifest() -> dict[str, Any]:
    """Return Temporal adapter registration contracts."""
    return temporal_registration_manifest()


@mcp.tool()
def acquire_write_lease(
    document_key: str,
    holder: str,
    scope: str = "project",
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Acquire a project write lease."""
    try:
        lease = _rt().project_store.acquire_lease(
            document_key, holder, scope=scope, ttl_seconds=ttl_seconds
        )
    except OperatorError as exc:
        raise ValueError(str(exc)) from exc
    return lease.model_dump(mode="json")


@mcp.tool()
def release_write_lease(document_key: str, holder: str) -> dict[str, str]:
    """Release a project write lease."""
    try:
        _rt().project_store.release_lease(document_key, holder)
    except OperatorError as exc:
        raise ValueError(str(exc)) from exc
    return {"status": "released"}


@mcp.tool()
def ingest_script(
    source: str,
    document_key: str,
    actor_id: str,
    authorization_scope: str,
    idempotency_key: str,
    rationale: str,
    title: str = "Untitled",
    revision: str = "0.1.0",
    format: str = "fountain",
    expected_state_hash: str | None = None,
) -> dict[str, Any]:
    """Lease-gated ingest: run kernel pipeline and store project artifacts.

    ``expected_state_hash`` must match project ``state_hash`` when re-ingesting
    an existing project (universal MutationEnvelope write contract).
    """
    envelope = MutationEnvelope.from_parts(
        actor_id=actor_id,
        authorization_scope=authorization_scope,
        idempotency_key=idempotency_key,
        rationale=rationale,
        expected_state_hash=expected_state_hash,
    )
    try:
        project, run = _rt().project_store.ingest_script(
            document_key=document_key,
            title=title,
            text=source,
            revision=revision,
            format=format,
            envelope=envelope,
        )
    except (OperatorError, PipelineError) as exc:
        raise ValueError(str(exc)) from exc
    return {
        "project": project.model_dump(mode="json"),
        "run": run.model_dump(mode="json"),
    }


@mcp.tool()
def get_project_status(document_key: str) -> dict[str, Any] | None:
    """Return operator project status."""
    return _rt().project_store.resource(f"cf://projects/{document_key}/status")


@mcp.tool()
def resolve_resource(uri: str) -> dict[str, Any] | None:
    """Resolve a cf:// resource URI."""
    return _rt().project_store.resource(uri)


@mcp.tool()
def audit_drift(document_key: str) -> list[dict[str, Any]]:
    """Return continuity drift diagnostics for a project ledger."""
    project = _rt().project_store.get_project(document_key)
    if project is None or not project.continuity_ledger:
        return []
    return [
        item
        for item in project.continuity_ledger.get("diagnostics") or []
        if str(item.get("code", "")).startswith("CL2")
    ]


@mcp.tool()
def inspect_scene(document_key: str, scene_id: str) -> dict[str, Any] | None:
    """Inspect a scene manifest for a registered project."""
    return _rt().project_store.resource(f"cf://scenes/{scene_id}/manifest")


@mcp.tool()
def inspect_character_state(document_key: str, character_name: str) -> dict[str, Any] | None:
    """Inspect character entity + facts from the project ledger."""
    project = _rt().project_store.get_project(document_key)
    if project is None or not project.continuity_ledger:
        return None
    ledger = project.continuity_ledger
    needle = character_name.casefold()
    entity = next(
        (
            e
            for e in ledger.get("entities") or []
            if e.get("kind") == "character" and needle in str(e.get("normalized_name", ""))
        ),
        None,
    )
    if entity is None:
        return None
    facts = [
        f
        for f in ledger.get("facts") or []
        if f.get("subject_entity_id") == entity.get("entity_id")
    ]
    return {"entity": entity, "facts": facts}


@mcp.tool()
def list_pipeline_runs(document_key: str) -> list[dict[str, Any]]:
    """List durable pipeline runs for a project."""
    return [
        run.model_dump(mode="json")
        for run in _rt().project_store.list_runs_for_project(document_key)
    ]


@mcp.tool()
def queue_generation(
    document_key: str,
    shot_id: str,
    actor_id: str = "mcp-operator",
    authorization_scope: str = "generation:preview",
    idempotency_key: str = "mcp-queue-generation",
    rationale: str = "PROPOSED generation (no canon write)",
    seed: str = "0",
) -> dict[str, Any]:
    """Generate a PROPOSED mock media candidate for a shot (no canon mutation).

    MutationEnvelope fields are validated for audit consistency; output remains
    PROPOSED and never becomes film canon.
    """
    MutationEnvelope.from_parts(
        actor_id=actor_id,
        authorization_scope=authorization_scope,
        idempotency_key=idempotency_key,
        rationale=rationale,
    )
    project = _rt().project_store.get_project(document_key)
    if project is None or not project.shot_contracts:
        raise ValueError("project or shot contracts not found")
    contract = next(
        (
            c
            for c in project.shot_contracts.get("contracts") or []
            if str(c.get("shot_id")) == shot_id
        ),
        None,
    )
    if contract is None:
        raise ValueError("shot not found")
    candidate = _rt().gateway.generate_for_shot(contract, seed=seed)
    artifact_store = _rt().artifact_store
    if artifact_store is not None:
        artifact_store.put(candidate)
    return candidate.model_dump(mode="json")


@mcp.tool()
def run_shot_repair_loop(
    document_key: str,
    shot_id: str,
    actor_id: str = "mcp-operator",
    authorization_scope: str = "generation:repair",
    idempotency_key: str = "mcp-shot-repair",
    rationale: str = "PROPOSED repair loop (no canon write)",
    seed: str = "0",
    max_attempts: int = 3,
    fail_first: bool = False,
) -> dict[str, Any]:
    """Run generate→validate→repair loop for one shot (mock worker).

    MutationEnvelope fields are validated for audit consistency; accepted
    candidates remain PROPOSED.
    """
    MutationEnvelope.from_parts(
        actor_id=actor_id,
        authorization_scope=authorization_scope,
        idempotency_key=idempotency_key,
        rationale=rationale,
    )
    project = _rt().project_store.get_project(document_key)
    if project is None or not project.shot_contracts:
        raise ValueError("project or shot contracts not found")
    contract = next(
        (
            c
            for c in project.shot_contracts.get("contracts") or []
            if str(c.get("shot_id")) == shot_id
        ),
        None,
    )
    if contract is None:
        raise ValueError("shot not found")
    result = run_repair_loop(
        contract,
        gateway=_rt().gateway,
        seed=seed,
        max_attempts=max_attempts,
        fail_first=fail_first,
    )
    artifact_store = _rt().artifact_store
    if result.accepted_candidate is not None and artifact_store is not None:
        artifact_store.put(result.accepted_candidate)
    return result.model_dump(mode="json")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
