# CONTINUITY_FORGE_CONTINUITY_LEDGER_001

## Goal

Build the deterministic M1 continuity ledger that turns validated Production IR into a
provenance-bearing registry of entities, scene contracts, state facts, and setup/payoff links.

## Canonical architecture

Architecture authority: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

M1 extends the deterministic kernel only. Temporal workflows, generation providers,
evaluator-repair loops, and mutating MCP tools remain deferred.

## Bounded sequence

1. Continuity ledger schema (entities, facts, scene contracts, setup/payoff)
2. Deterministic entity registry from character cues and slugline locations
3. Presence, enter/exit, prop, wardrobe, and injury fact extraction with atom provenance
4. Scene continuity contracts
5. Setup/payoff linking for recurring entities
6. Read-only REST and MCP ledger surfaces
7. Golden fixture gates on continuity-heavy screenplays
8. M1 validation receipt

## M1 exit gate

```yaml
ledger_builds_from_production_ir: PASS
entity_ids_stable: 1.0
every_fact_has_atom_provenance: PASS
scene_contracts_cover_all_scenes: PASS
setup_payoff_links_deterministic: PASS
rest_and_mcp_ledger_contracts: PASS
ruff_mypy_pytest: PASS
```

## Authority rules

- Production IR remains the sole narrative atom authority.
- Ledger facts are derived, validated, and never invent source text.
- Heuristic extractions are labeled `heuristic`; cue/slugline facts are `deterministic`.
- Model proposals may suggest aliases or missing links later; they cannot mutate the ledger.
- No persistence layer is required in M1 (stateless build from compile output).

## Explicit exclusions

- Video or image generation
- Visual-bible generation
- Temporal production workflows
- Provider gateway execution
- Generator-evaluator repair loops
- Autonomous rewriting
- Direct agent database mutation
- Shot contract compilation (M2)

## Post-M1 continuation

```text
M2 SHOT CONTRACT COMPILER
-> M3 DURABLE HARNESS / TEMPORAL
-> M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 CONTROLLED 30-60 SECOND PROOF
```
