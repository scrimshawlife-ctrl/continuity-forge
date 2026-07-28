# CONTINUITY_FORGE_SHOT_CONTRACTS_001

## Goal

Build the deterministic M2 shot-contract compiler that turns Production IR and the
continuity ledger into model-neutral shot contracts with hard constraints, soft
targets, prohibitions, and start/end state hashes.

## Canonical architecture

Architecture authority: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

Shot contracts are kernel outputs. Generators may consume them later; they cannot
author or mutate contracts.

## Bounded sequence

1. Shot contract schema
2. Deterministic compiler from Production IR + Continuity Ledger
3. Per-scene contracts with required atoms and entity constraints
4. Start/end state hashes over ledger facts
5. Provider capability stubs (declarative only)
6. Read-only REST, MCP, and CLI surfaces
7. Golden/unit gates
8. M2 validation receipt

## M2 exit gate

```yaml
contracts_cover_all_scenes: PASS
required_atoms_provenance: PASS
hard_constraints_from_ledger: PASS
start_end_state_hashes_stable: PASS
rest_mcp_cli_contracts: PASS
ruff_mypy_pytest: PASS
```

## Authority rules

- Production IR owns narrative atoms.
- Continuity ledger owns derived entity/fact state.
- Shot contracts reference both; they invent no new story content.
- Provider capability fields are declarative requirements, not executions.
- No media generation, Temporal, or mutating MCP tools in M2.

## Explicit exclusions

- Image/video/voice generation
- Provider gateway execution
- Temporal workflows
- Evaluator-repair loops
- Autonomous rewriting
- Visual-bible systems

## Post-M2 continuation

```text
M3 DURABLE HARNESS / TEMPORAL
-> M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 CONTROLLED 30-60 SECOND PROOF
```
