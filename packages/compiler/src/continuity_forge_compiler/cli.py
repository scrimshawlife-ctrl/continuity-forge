import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from continuity_forge_harness import PipelineCommand, execute_kernel_pipeline
from continuity_forge_ledger import build_continuity_ledger
from continuity_forge_shots import compile_shot_contracts

from .compiler import compile_file

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    """Compile screenplays into Production IR, ledgers, shot contracts, and pipeline runs."""


@app.command("compile")
def compile_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a Fountain/FDX screenplay to validated Production IR JSON."""
    document = compile_file(script, document_key=document_key)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.production-ir.json"
    target.write_text(document.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("ledger")
def ledger_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a screenplay and write the derived continuity ledger JSON."""
    document = compile_file(script, document_key=document_key)
    ledger = build_continuity_ledger(document)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.continuity-ledger.json"
    target.write_text(ledger.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("shots")
def shots_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Compile a screenplay and write model-neutral shot contracts JSON."""
    document = compile_file(script, document_key=document_key)
    bundle = compile_shot_contracts(document)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.shot-contracts.json"
    target.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("pipeline")
def pipeline_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
    actor_id: Annotated[str, typer.Option("--actor-id")] = "cli-operator",
    scope: Annotated[str, typer.Option("--scope")] = "kernel:pipeline",
    idempotency_key: Annotated[str | None, typer.Option("--idempotency-key")] = None,
    rationale: Annotated[str, typer.Option("--rationale")] = "CLI kernel pipeline execution",
) -> None:
    """Run the durable compile → ledger → shots pipeline and write the run receipt."""
    text = script.read_text(encoding="utf-8")
    fmt = "fdx" if script.suffix.casefold() == ".fdx" else "fountain"
    command = PipelineCommand(
        actor_id=actor_id,
        authorization_scope=scope,
        idempotency_key=idempotency_key or f"cli-{uuid4()}",
        rationale=rationale,
        title=script.stem,
        text=text,
        document_key=document_key or script.stem,
        format=fmt,  # type: ignore[arg-type]
    )
    run = execute_kernel_pipeline(command)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.pipeline-run.json"
    target.write_text(run.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("proof")
def proof_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    out: Annotated[Path, typer.Option("--out")] = Path("out"),
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
    seed: Annotated[str, typer.Option("--seed")] = "proof",
) -> None:
    """Run the controlled M7 proof (mock media) and write a proof receipt."""
    from continuity_forge_repair.proof import run_controlled_proof

    receipt = run_controlled_proof(script, document_key=document_key, seed=seed)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{script.stem}.proof-receipt.json"
    target.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(str(target))


@app.command("worker-check")
def worker_check_cmd(
    host: Annotated[str | None, typer.Option("--host")] = None,
    namespace: Annotated[str | None, typer.Option("--namespace")] = None,
    task_queue: Annotated[str | None, typer.Option("--task-queue")] = None,
) -> None:
    """Print Temporal worker registration spec without connecting to a cluster."""
    from continuity_forge_harness import build_worker_spec, try_build_temporal_worker_note

    spec = build_worker_spec(task_queue=task_queue, target_host=host, namespace=namespace)
    typer.echo(
        json.dumps({"spec": spec.as_dict(), "temporal": try_build_temporal_worker_note()}, indent=2)
    )


@app.command("worker-dry-run")
def worker_dry_run_cmd(
    script: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    store_root: Annotated[Path | None, typer.Option("--store-root")] = None,
    document_key: Annotated[str | None, typer.Option("--document-key")] = None,
) -> None:
    """Run KernelPipelineWorkflow via the in-process Temporal-shaped worker."""
    from continuity_forge_harness import (
        FileRunStore,
        InProcessWorker,
        PipelineCommand,
        try_build_temporal_worker_note,
    )

    text = script.read_text(encoding="utf-8")
    fmt = "fdx" if script.suffix.casefold() == ".fdx" else "fountain"
    store = FileRunStore(store_root) if store_root is not None else None
    worker = InProcessWorker(store=store)
    command = PipelineCommand(
        actor_id="cli-worker",
        authorization_scope="kernel:pipeline",
        idempotency_key=f"worker-{uuid4()}",
        rationale="In-process worker dry-run",
        title=script.stem,
        text=text,
        document_key=document_key or script.stem,
        format=fmt,  # type: ignore[arg-type]
    )
    result = worker.run_workflow(command)
    typer.echo(json.dumps({"status": result.get("status"), "run_id": result.get("run_id")}))
    typer.echo(json.dumps(try_build_temporal_worker_note()))


if __name__ == "__main__":
    app()
