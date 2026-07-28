"""Temporal worker entrypoint contracts (optional temporalio).

This module never imports temporalio at module import time so the core package
stays installable without the optional extra. Use `build_worker_spec()` offline
and `run_temporal_worker()` when temporalio + cluster are available.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .activities import (
    activity_build_continuity_ledger,
    activity_compile_screenplay,
    activity_compile_shot_contracts,
    activity_run_kernel_pipeline,
)
from .temporal_adapter import TASK_QUEUE, WORKFLOW_TYPE


@dataclass(frozen=True)
class WorkerSpec:
    workflow_type: str
    task_queue: str
    activities: tuple[str, ...]
    target_host: str
    namespace: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow_type": self.workflow_type,
            "task_queue": self.task_queue,
            "activities": list(self.activities),
            "target_host": self.target_host,
            "namespace": self.namespace,
        }


def build_worker_spec(
    *,
    task_queue: str | None = None,
    target_host: str | None = None,
    namespace: str | None = None,
) -> WorkerSpec:
    return WorkerSpec(
        workflow_type=WORKFLOW_TYPE,
        task_queue=task_queue or os.environ.get("CF_TEMPORAL_TASK_QUEUE") or TASK_QUEUE,
        activities=(
            "compile_screenplay",
            "build_continuity_ledger",
            "compile_shot_contracts",
            "run_kernel_pipeline",
        ),
        target_host=target_host or os.environ.get("CF_TEMPORAL_HOST") or "localhost:7233",
        namespace=namespace or os.environ.get("CF_TEMPORAL_NAMESPACE") or "default",
    )


def run_temporal_worker(
    *,
    task_queue: str | None = None,
    target_host: str | None = None,
    namespace: str | None = None,
) -> None:
    """Connect to Temporal and run a worker until interrupted.

    Requires optional dependency: pip install 'continuity-forge[temporal]'
    """
    try:
        from temporalio import activity, workflow  # type: ignore[import-not-found]
        from temporalio.client import Client  # type: ignore[import-not-found]
        from temporalio.worker import Worker  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "temporalio is not installed. Install with: pip install 'continuity-forge[temporal]'"
        ) from exc

    spec = build_worker_spec(task_queue=task_queue, target_host=target_host, namespace=namespace)

    @activity.defn(name="compile_screenplay")  # type: ignore[untyped-decorator]
    async def compile_screenplay(payload: dict[str, Any]) -> dict[str, Any]:
        return activity_compile_screenplay(payload)

    @activity.defn(name="build_continuity_ledger")  # type: ignore[untyped-decorator]
    async def build_continuity_ledger_act(payload: dict[str, Any]) -> dict[str, Any]:
        return activity_build_continuity_ledger(payload)

    @activity.defn(name="compile_shot_contracts")  # type: ignore[untyped-decorator]
    async def compile_shot_contracts_act(payload: dict[str, Any]) -> dict[str, Any]:
        return activity_compile_shot_contracts(payload)

    @activity.defn(name="run_kernel_pipeline")  # type: ignore[untyped-decorator]
    async def run_kernel_pipeline_act(payload: dict[str, Any]) -> dict[str, Any]:
        return activity_run_kernel_pipeline(payload)

    @workflow.defn(name=WORKFLOW_TYPE)
    class KernelPipelineWorkflow:
        @workflow.run  # type: ignore[untyped-decorator]
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            result: Any = await workflow.execute_activity(
                run_kernel_pipeline_act,
                payload,
                start_to_close_timeout=__import__("datetime").timedelta(minutes=10),
            )
            return dict(result)

    async def _main() -> None:
        client = await Client.connect(spec.target_host, namespace=spec.namespace)
        worker = Worker(
            client,
            task_queue=spec.task_queue,
            workflows=[KernelPipelineWorkflow],
            activities=[
                compile_screenplay,
                build_continuity_ledger_act,
                compile_shot_contracts_act,
                run_kernel_pipeline_act,
            ],
        )
        await worker.run()

    import asyncio

    asyncio.run(_main())


def worker_cli(argv: list[str] | None = None) -> int:
    """Programmatic CLI for continuity-forge-worker (returns exit code)."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Continuity Forge Temporal worker")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print worker spec and exit (no cluster connection)",
    )
    parser.add_argument("--host", default=None, help="Temporal host:port")
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--task-queue", default=None)
    args = parser.parse_args(argv)

    spec = build_worker_spec(
        task_queue=args.task_queue,
        target_host=args.host,
        namespace=args.namespace,
    )
    if args.check:
        sys.stdout.write(json.dumps(spec.as_dict(), indent=2) + "\n")
        return 0
    try:
        run_temporal_worker(
            task_queue=args.task_queue,
            target_host=args.host,
            namespace=args.namespace,
        )
    except RuntimeError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    return 0


def worker_main() -> None:
    """Console script entrypoint."""
    raise SystemExit(worker_cli())
