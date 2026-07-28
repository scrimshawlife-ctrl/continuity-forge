"""Build dependency graphs from IR + shot contracts (no provider/S3 imports)."""

from __future__ import annotations

from continuity_forge_ir import ScriptDocument
from continuity_forge_ir.dependency_graph import (
    ChangeSet,
    DependencyGraph,
    StaleReport,
    build_graph,
    compute_stale,
    stale_shot_ids,
)

from continuity_forge_shots.models import ShotContractBundle


def build_graph_from_document_and_bundle(
    document: ScriptDocument,
    bundle: ShotContractBundle,
    *,
    proposed_by_shot: list[tuple[str, str]] | None = None,
) -> DependencyGraph:
    """Wire source → scenes → atoms → shot contracts (+ optional PROPOSED)."""
    scenes: list[tuple[str, list[str]]] = []
    for scene in document.scenes:
        atom_ids = [str(a.atom_id) for a in scene.atoms]
        scenes.append((str(scene.scene_id), atom_ids))

    shots: list[tuple[str, str, list[str], list[str]]] = []
    for contract in bundle.contracts:
        shots.append(
            (
                str(contract.shot_id),
                str(contract.scene_id),
                [str(a) for a in contract.required_atom_ids],
                [str(e) for e in contract.required_entity_ids],
            )
        )

    return build_graph(
        source_key=document.source_hash,
        scenes=scenes,
        shots=shots,
        proposed_by_shot=proposed_by_shot or [],
    )


def preview_invalidation(
    document: ScriptDocument,
    bundle: ShotContractBundle,
    change: ChangeSet,
    *,
    force_full: bool = False,
    proposed_by_shot: list[tuple[str, str]] | None = None,
) -> StaleReport:
    graph = build_graph_from_document_and_bundle(
        document, bundle, proposed_by_shot=proposed_by_shot
    )
    return compute_stale(graph, change, force_full=force_full)


__all__ = [
    "ChangeSet",
    "DependencyGraph",
    "StaleReport",
    "build_graph_from_document_and_bundle",
    "preview_invalidation",
    "stale_shot_ids",
]
