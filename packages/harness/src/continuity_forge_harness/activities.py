"""Temporal-ready activity callables (pure; no cluster required)."""

from __future__ import annotations

from typing import Any

from continuity_forge_compiler import compile_fdx_text, compile_text
from continuity_forge_ir import content_hash
from continuity_forge_ledger import build_continuity_ledger
from continuity_forge_shots import compile_shot_contracts

from .models import PipelineCommand, PipelineStepName
from .pipeline import execute_kernel_pipeline
from .store import RunStore


def activity_compile_screenplay(command_payload: dict[str, Any]) -> dict[str, Any]:
    command = PipelineCommand.model_validate(command_payload)
    compiler = compile_fdx_text if command.format == "fdx" else compile_text
    document = compiler(
        command.text,
        title=command.title,
        revision=command.revision,
        document_key=command.document_key,
    )
    return {
        "step": PipelineStepName.COMPILE.value,
        "production_ir": document.model_dump(mode="json"),
        "output_hash": content_hash(document.model_dump_json()),
    }


def activity_build_continuity_ledger(command_payload: dict[str, Any]) -> dict[str, Any]:
    command = PipelineCommand.model_validate(command_payload)
    compiler = compile_fdx_text if command.format == "fdx" else compile_text
    document = compiler(
        command.text,
        title=command.title,
        revision=command.revision,
        document_key=command.document_key,
    )
    ledger = build_continuity_ledger(document)
    return {
        "step": PipelineStepName.LEDGER.value,
        "continuity_ledger": ledger.model_dump(mode="json"),
        "output_hash": content_hash(ledger.model_dump_json(exclude={"diagnostics"})),
    }


def activity_compile_shot_contracts(command_payload: dict[str, Any]) -> dict[str, Any]:
    command = PipelineCommand.model_validate(command_payload)
    compiler = compile_fdx_text if command.format == "fdx" else compile_text
    document = compiler(
        command.text,
        title=command.title,
        revision=command.revision,
        document_key=command.document_key,
    )
    ledger = build_continuity_ledger(document)
    shots = compile_shot_contracts(document, ledger=ledger)
    return {
        "step": PipelineStepName.SHOTS.value,
        "shot_contracts": shots.model_dump(mode="json"),
        "output_hash": content_hash(shots.model_dump_json(exclude={"diagnostics"})),
    }


def activity_run_kernel_pipeline(
    command_payload: dict[str, Any],
    *,
    store: RunStore | None = None,
) -> dict[str, Any]:
    """Full pipeline activity used by in-process Temporal-shaped workers."""
    command = PipelineCommand.model_validate(command_payload)
    run = execute_kernel_pipeline(command, store=store)
    return run.model_dump(mode="json")


ACTIVITY_CALLABLES: dict[str, Any] = {
    PipelineStepName.COMPILE.value: activity_compile_screenplay,
    PipelineStepName.LEDGER.value: activity_build_continuity_ledger,
    PipelineStepName.SHOTS.value: activity_compile_shot_contracts,
    "run_kernel_pipeline": activity_run_kernel_pipeline,
}
