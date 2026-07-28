"""Deterministic dependency graph + invalidation (pure; no providers/S3).

Edges (minimum campaign 4.3):

  source → scenes → atoms
  scenes → shot_contracts
  atoms → shot_contracts
  entities → facts → shot_contracts (optional)
  shot_contracts → proposed_candidates (optional)

Invalidation never elevates PROPOSED to canon — it only marks descendants stale
while preserving prior hashes/lineage for the operator.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactKind(StrEnum):
    SOURCE = "source"
    SCENE = "scene"
    ATOM = "atom"
    ENTITY = "entity"
    FACT = "fact"
    SHOT_CONTRACT = "shot_contract"
    PROPOSED_CANDIDATE = "proposed_candidate"


def artifact_id(kind: ArtifactKind | str, key: str) -> str:
    """Stable node id: ``{kind}:{key}``."""
    k = kind.value if isinstance(kind, ArtifactKind) else str(kind)
    return f"{k}:{key}"


class ChangeSet(BaseModel):
    """Scoped dirty set supplied by an operator or recompute planner."""

    source_changed: bool = False
    scene_ids: list[str] = Field(default_factory=list)
    atom_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    fact_ids: list[str] = Field(default_factory=list)
    shot_ids: list[str] = Field(default_factory=list)


class StaleReport(BaseModel):
    """Deterministic invalidation result (sorted ids)."""

    stale_ids: list[str] = Field(default_factory=list)
    seed_ids: list[str] = Field(default_factory=list)
    force_full: bool = False
    edges_traversed: int = 0
    # Explicit product rule — UI and agents must surface this.
    authority_note: str = (
        "Invalidation marks lineage stale only; PROPOSED candidates are never "
        "elevated to canon by this operation."
    )


class DependencyGraph(BaseModel):
    """Directed parent → child edges (change propagates parent → descendants)."""

    nodes: list[str] = Field(default_factory=list)
    # parent_id -> sorted unique children
    children: dict[str, list[str]] = Field(default_factory=dict)

    def add_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            self.nodes.append(node_id)

    def add_edge(self, parent: str, child: str) -> None:
        self.add_node(parent)
        self.add_node(child)
        bucket = self.children.setdefault(parent, [])
        if child not in bucket:
            bucket.append(child)

    def freeze(self) -> DependencyGraph:
        """Sort nodes and child lists for deterministic traversal order."""
        self.nodes = sorted(set(self.nodes))
        frozen: dict[str, list[str]] = {}
        for parent, kids in sorted(self.children.items()):
            frozen[parent] = sorted(set(kids))
        self.children = frozen
        return self


def build_graph(
    *,
    source_key: str = "document",
    scenes: Iterable[tuple[str, Iterable[str]]] = (),
    shots: Iterable[tuple[str, str, Iterable[str], Iterable[str]]] = (),
    entities: Iterable[tuple[str, Iterable[str]]] = (),
    proposed_by_shot: Iterable[tuple[str, str]] = (),
) -> DependencyGraph:
    """Build a production dependency graph from plain id maps.

    scenes: (scene_id, atom_ids)
    shots: (shot_id, scene_id, required_atom_ids, required_entity_ids)
    entities: (entity_id, fact_ids)
    proposed_by_shot: (candidate_id, shot_id)
    """
    g = DependencyGraph()
    source = artifact_id(ArtifactKind.SOURCE, source_key)
    g.add_node(source)

    for scene_id, atom_ids in scenes:
        scene_node = artifact_id(ArtifactKind.SCENE, str(scene_id))
        g.add_edge(source, scene_node)
        for atom in atom_ids:
            atom_node = artifact_id(ArtifactKind.ATOM, str(atom))
            g.add_edge(scene_node, atom_node)

    entity_nodes: dict[str, str] = {}
    for entity_id, fact_ids in entities:
        e_node = artifact_id(ArtifactKind.ENTITY, str(entity_id))
        entity_nodes[str(entity_id)] = e_node
        g.add_node(e_node)
        for fact in fact_ids:
            f_node = artifact_id(ArtifactKind.FACT, str(fact))
            g.add_edge(e_node, f_node)

    for shot_id, scene_id, atom_ids, entity_ids in shots:
        shot_node = artifact_id(ArtifactKind.SHOT_CONTRACT, str(shot_id))
        scene_node = artifact_id(ArtifactKind.SCENE, str(scene_id))
        g.add_edge(scene_node, shot_node)
        for atom in atom_ids:
            g.add_edge(artifact_id(ArtifactKind.ATOM, str(atom)), shot_node)
        for entity in entity_ids:
            e_key = str(entity)
            e_node = entity_nodes.get(e_key) or artifact_id(ArtifactKind.ENTITY, e_key)
            g.add_edge(e_node, shot_node)

    for candidate_id, shot_id in proposed_by_shot:
        cand = artifact_id(ArtifactKind.PROPOSED_CANDIDATE, str(candidate_id))
        shot_node = artifact_id(ArtifactKind.SHOT_CONTRACT, str(shot_id))
        # PROPOSED hangs off contracts; never reverse edge into canon.
        g.add_edge(shot_node, cand)

    return g.freeze()


def compute_stale(
    graph: DependencyGraph,
    change: ChangeSet,
    *,
    force_full: bool = False,
) -> StaleReport:
    """Return deterministic set of stale artifact ids under the change set.

    If ``force_full`` or ``change.source_changed``, every non-source node is stale.
    Otherwise seeds are expanded by following parent→child edges (descendants only).
    """
    g = graph.freeze()
    if force_full or change.source_changed:
        full_stale = sorted(n for n in g.nodes if not n.startswith(f"{ArtifactKind.SOURCE}:"))
        full_seeds = sorted(n for n in g.nodes if n.startswith(f"{ArtifactKind.SOURCE}:"))
        if not full_seeds:
            full_seeds = [artifact_id(ArtifactKind.SOURCE, "document")]
        return StaleReport(
            stale_ids=full_stale,
            seed_ids=full_seeds,
            force_full=True,
            edges_traversed=sum(len(v) for v in g.children.values()),
        )

    raw_seeds: list[str] = []
    for sid in change.scene_ids:
        raw_seeds.append(artifact_id(ArtifactKind.SCENE, str(sid)))
    for aid in change.atom_ids:
        raw_seeds.append(artifact_id(ArtifactKind.ATOM, str(aid)))
    for eid in change.entity_ids:
        raw_seeds.append(artifact_id(ArtifactKind.ENTITY, str(eid)))
    for fid in change.fact_ids:
        raw_seeds.append(artifact_id(ArtifactKind.FACT, str(fid)))
    for shid in change.shot_ids:
        raw_seeds.append(artifact_id(ArtifactKind.SHOT_CONTRACT, str(shid)))

    # Only seeds that exist in the graph participate (unknown ids are ignored).
    node_set = set(g.nodes)
    seed_set = sorted({s for s in raw_seeds if s in node_set})
    if not seed_set:
        return StaleReport(stale_ids=[], seed_ids=[], force_full=False, edges_traversed=0)

    visited: set[str] = set()
    edges = 0
    q: deque[str] = deque(seed_set)
    while q:
        node = q.popleft()
        if node in visited:
            continue
        visited.add(node)
        for child in g.children.get(node, []):
            edges += 1
            if child not in visited:
                q.append(child)

    return StaleReport(
        stale_ids=sorted(visited),
        seed_ids=seed_set,
        force_full=False,
        edges_traversed=edges,
    )


def children_index(graph: DependencyGraph) -> dict[str, list[str]]:
    """Copy of children map (for tests / debugging)."""
    g = graph.freeze()
    return {k: list(v) for k, v in g.children.items()}


def adjacency_for_tests(graph: DependencyGraph) -> dict[str, list[str]]:
    """Alias used by architecture/unit tests."""
    return children_index(graph)


def stale_shot_ids(report: StaleReport) -> list[str]:
    """Extract bare shot_contract keys from a stale report."""
    prefix = f"{ArtifactKind.SHOT_CONTRACT}:"
    return sorted(node[len(prefix) :] for node in report.stale_ids if node.startswith(prefix))
