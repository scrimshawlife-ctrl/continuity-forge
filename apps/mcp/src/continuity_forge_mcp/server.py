from __future__ import annotations

from typing import Any
from uuid import UUID

from continuity_forge_compiler import compile_fdx_text, compile_text
from continuity_forge_harness import (
    DEFAULT_RUN_STORE,
    PipelineCommand,
    PipelineError,
    execute_kernel_pipeline,
    temporal_registration_manifest,
)
from continuity_forge_ir import ScriptDocument
from continuity_forge_ledger import ContinuityLedger, build_continuity_ledger
from continuity_forge_shots import ShotContractBundle, compile_shot_contracts
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Continuity Forge")


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
    """Compile Fountain or Final Draft XML without mutating canonical state."""
    return _compile(source, title, document_key, format, revision).model_dump(mode="json")


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
        run = execute_kernel_pipeline(command, store=DEFAULT_RUN_STORE)
    except PipelineError as exc:
        raise ValueError(str(exc)) from exc
    return run.model_dump(mode="json")


@mcp.tool()
def get_pipeline_run(run_id: str) -> dict[str, Any] | None:
    """Fetch a durable pipeline run by ID."""
    run = DEFAULT_RUN_STORE.get(UUID(run_id))
    return None if run is None else run.model_dump(mode="json")


@mcp.tool()
def get_temporal_manifest() -> dict[str, Any]:
    """Return Temporal adapter registration contracts."""
    return temporal_registration_manifest()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
