"""Incremental compile: full parse + prior-IR reconcile + invalidation preview.

Always validates the full document (coverage partition intact). Scene/atom IDs
for unchanged content are stable when ``prior`` is supplied. Downstream
dependency invalidation marks affected shot contracts stale without elevating
PROPOSED candidates to canon.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from continuity_forge_ir import (
    ChangeSet,
    ScriptDocument,
    StaleReport,
    content_hash,
    stale_shot_ids,
)
from continuity_forge_shots import compile_shot_contracts, preview_invalidation
from pydantic import BaseModel, Field

from .compiler import compile_text
from .fdx import compile_fdx_text
from .reconcile import _scene_fingerprint  # intentional: shared pure fingerprint


class SceneCompileStatus(StrEnum):
    CARRIED = "carried"
    RECOMPILED = "recompiled"
    ADDED = "added"
    REMOVED = "removed"


class SceneCompileDelta(BaseModel):
    scene_id: str
    slugline: str
    status: SceneCompileStatus
    ordinal: int | None = None


class IncrementalCompileResult(BaseModel):
    """Result of an incremental compile (read-side; not a canon write by itself)."""

    document: ScriptDocument
    mode: str = "incremental"
    claim: str = "incremental_compile_not_production_ready"
    prior_source_hash: str | None = None
    base_ir_hash: str | None = None
    prior_reconciled: bool = False
    carried_scene_ids: list[str] = Field(default_factory=list)
    recompiled_scene_ids: list[str] = Field(default_factory=list)
    added_scene_ids: list[str] = Field(default_factory=list)
    removed_scene_ids: list[str] = Field(default_factory=list)
    scene_deltas: list[SceneCompileDelta] = Field(default_factory=list)
    coverage_accounted_characters: int = 0
    coverage_source_characters: int = 0
    coverage_carried_scenes: int = 0
    coverage_recompiled_scenes: int = 0
    invalidation: StaleReport | None = None
    stale_shot_ids: list[str] = Field(default_factory=list)
    authority_note: str = (
        "Incremental compile validates the full IR partition; carried scenes retain "
        "stable ids only. PROPOSED media is never elevated to canon. Not production film."
    )


def _scene_map(document: ScriptDocument) -> dict[UUID, Any]:
    return {scene.scene_id: scene for scene in document.scenes}


def classify_scene_deltas(
    current: ScriptDocument,
    prior: ScriptDocument | None,
) -> list[SceneCompileDelta]:
    """Classify each scene as carried / recompiled / added / removed."""
    if prior is None:
        return [
            SceneCompileDelta(
                scene_id=str(scene.scene_id),
                slugline=scene.slugline,
                status=SceneCompileStatus.RECOMPILED,
                ordinal=scene.ordinal,
            )
            for scene in current.scenes
        ]

    prior_by_id = _scene_map(prior)
    current_by_id = _scene_map(current)
    deltas: list[SceneCompileDelta] = []

    for scene in current.scenes:
        prior_scene = prior_by_id.get(scene.scene_id)
        if prior_scene is None:
            status = SceneCompileStatus.ADDED
        elif _scene_fingerprint(prior_scene) == _scene_fingerprint(scene):
            status = SceneCompileStatus.CARRIED
        else:
            status = SceneCompileStatus.RECOMPILED
        deltas.append(
            SceneCompileDelta(
                scene_id=str(scene.scene_id),
                slugline=scene.slugline,
                status=status,
                ordinal=scene.ordinal,
            )
        )

    for scene in prior.scenes:
        if scene.scene_id not in current_by_id:
            deltas.append(
                SceneCompileDelta(
                    scene_id=str(scene.scene_id),
                    slugline=scene.slugline,
                    status=SceneCompileStatus.REMOVED,
                    ordinal=scene.ordinal,
                )
            )

    # Deterministic order: current ordinals then removed
    deltas.sort(
        key=lambda d: (
            0 if d.status != SceneCompileStatus.REMOVED else 1,
            d.ordinal if d.ordinal is not None else 10**9,
            d.scene_id,
        )
    )
    return deltas


def compile_incremental(
    text: str,
    *,
    title: str = "Untitled",
    revision: str = "0.1.0",
    document_key: str | None = None,
    format: str = "fountain",
    prior: ScriptDocument | None = None,
    force_full_invalidation: bool = False,
) -> IncrementalCompileResult:
    """Full schema-validated compile with prior-ID reconcile + invalidation preview.

    Empty change (identical source to prior) yields all scenes **carried** and empty
    stale set. Partial edits recompile the whole IR for coverage integrity while
    preserving stable ids via ``prior`` and marking only dirty subgraphs stale.
    """
    compiler = compile_fdx_text if format == "fdx" else compile_text
    document = compiler(
        text,
        title=title,
        revision=revision,
        document_key=document_key,
        prior=prior,
    )

    prior_reconciled = prior is not None and document.script_id == (
        prior.script_id if prior else None
    )
    deltas = classify_scene_deltas(document, prior if prior_reconciled else None)

    carried = [d.scene_id for d in deltas if d.status == SceneCompileStatus.CARRIED]
    recompiled = [d.scene_id for d in deltas if d.status == SceneCompileStatus.RECOMPILED]
    added = [d.scene_id for d in deltas if d.status == SceneCompileStatus.ADDED]
    removed = [d.scene_id for d in deltas if d.status == SceneCompileStatus.REMOVED]

    source_changed = prior is None or prior.source_hash != document.source_hash
    change = ChangeSet(
        source_changed=force_full_invalidation or (source_changed and not carried),
        scene_ids=sorted(set(recompiled + added + removed)),
    )
    # If only some scenes changed, seed those scenes (not whole source) when
    # we still have carried content — more precise stale set.
    if source_changed and carried and not force_full_invalidation:
        change = ChangeSet(
            source_changed=False,
            scene_ids=sorted(set(recompiled + added + removed)),
        )
    if not source_changed and prior is not None:
        change = ChangeSet()

    bundle = compile_shot_contracts(document)
    inv = preview_invalidation(
        document,
        bundle,
        change,
        force_full=force_full_invalidation,
    )

    base_hash = content_hash(prior.model_dump_json()) if prior is not None else None

    return IncrementalCompileResult(
        document=document,
        prior_source_hash=prior.source_hash if prior else None,
        base_ir_hash=base_hash,
        prior_reconciled=bool(prior_reconciled),
        carried_scene_ids=carried,
        recompiled_scene_ids=recompiled,
        added_scene_ids=added,
        removed_scene_ids=removed,
        scene_deltas=deltas,
        coverage_accounted_characters=document.coverage.accounted_characters,
        coverage_source_characters=document.coverage.source_characters,
        coverage_carried_scenes=len(carried),
        coverage_recompiled_scenes=len(recompiled) + len(added),
        invalidation=inv,
        stale_shot_ids=stale_shot_ids(inv),
    )
