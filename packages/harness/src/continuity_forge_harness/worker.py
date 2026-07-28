"""In-process Temporal-shaped worker and optional temporalio bootstrap."""

from __future__ import annotations

from typing import Any

from .activities import ACTIVITY_CALLABLES, activity_run_kernel_pipeline
from .models import PipelineCommand
from .store import RunStore
from .temporal_adapter import TASK_QUEUE, WORKFLOW_TYPE, temporal_registration_manifest


class InProcessWorker:
    """Executes registered activities without a Temporal cluster."""

    def __init__(self, store: RunStore | None = None) -> None:
        self.store = store
        self.task_queue = TASK_QUEUE
        self.workflow_type = WORKFLOW_TYPE

    def list_activities(self) -> list[str]:
        return sorted(ACTIVITY_CALLABLES)

    def execute(self, activity_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if activity_name not in ACTIVITY_CALLABLES:
            raise KeyError(f"unknown activity: {activity_name}")
        if activity_name == "run_kernel_pipeline":
            return activity_run_kernel_pipeline(payload, store=self.store)
        fn = ACTIVITY_CALLABLES[activity_name]
        result: dict[str, Any] = fn(payload)
        return result

    def run_workflow(self, command: PipelineCommand) -> dict[str, Any]:
        """KernelPipelineWorkflow equivalent: single activity orchestrating the pipeline."""
        return self.execute("run_kernel_pipeline", command.model_dump(mode="json"))

    def manifest(self) -> dict[str, Any]:
        base = temporal_registration_manifest()
        base["runtime"] = "in_process"
        base["activities"] = self.list_activities()
        return base


def try_build_temporal_worker_note() -> dict[str, Any]:
    """Return bootstrap notes; real temporalio worker is optional at install time."""
    try:
        import temporalio  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return {
            "temporalio_installed": False,
            "message": (
                "Install optional extra `pip install 'continuity-forge[temporal]'` "
                "and run continuity-forge-worker against a Temporal cluster."
            ),
            "task_queue": TASK_QUEUE,
            "workflow_type": WORKFLOW_TYPE,
        }
    return {
        "temporalio_installed": True,
        "message": "temporalio is installed; use continuity-forge-worker entrypoint.",
        "task_queue": TASK_QUEUE,
        "workflow_type": WORKFLOW_TYPE,
        "version": getattr(temporalio, "__version__", "unknown"),
    }
