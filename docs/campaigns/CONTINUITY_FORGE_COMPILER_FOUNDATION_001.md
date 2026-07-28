# CONTINUITY_FORGE_COMPILER_FOUNDATION_001

## Goal

Build the deterministic M0 compiler spine that converts screenplay source into validated, provenance-preserving Production IR.

## Canonical architecture

Continuity Forge is a deterministic cinematic-production kernel surrounded by a model-agnostic production harness.

Architecture authority: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

M0 builds the kernel foundation only. Temporal workflows, generation providers, evaluator-repair loops, and mutating MCP tools begin only after the M0 exit gate.

## Bounded sequence

1. Repository bootstrap
2. Schema bundle
3. Fountain ingestion
4. FDX ingestion
5. Narrative atomizer
6. Production IR
7. Typed diagnostics
8. Coverage accounting
9. Golden corpus
10. REST and read-only MCP contracts
11. M0 validation receipt

## M0 exit gate

```yaml
parse_success_rate: 1.0_on_supported_golden_corpus
silent_omission_count: 0
stable_id_reproducibility: 1.0
schema_validation: PASS
source_provenance_coverage: 1.0
deterministic_recompile: PASS
```

## Authority rules

- Source text is immutable input.
- Deterministic compiler output becomes canonical only after schema and invariant validation.
- Model outputs are proposals, never direct state mutations.
- Agent memory and workflow checkpoints are not canonical project state.
- Future mutations require actor identity, authorization, idempotency, expected-state hash, command version, and rationale.

## Explicit exclusions

- Video or image generation
- Visual-bible generation
- Temporal production workflows
- Provider gateway execution
- Generator-evaluator repair loops
- Autonomous adaptation or rewriting
- Direct agent database mutation
- Feature-length readiness claims

## Post-M0 continuation

```text
M1 CONTINUITY LEDGER
-> M2 SHOT CONTRACT COMPILER
-> M3 DURABLE HARNESS / TEMPORAL
-> M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 CONTROLLED 30-60 SECOND PROOF
```
