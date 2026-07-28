# CONTINUITY_FORGE_DURABLE_HARNESS_001

## Goal

Build the M3 durable production harness that runs the deterministic kernel pipeline
(compile → continuity ledger → shot contracts) under typed workflow commands with
idempotency, checkpoints, and recovery semantics. Temporal is the target runtime;
M3 ships a pure-Python harness core plus Temporal adapter contracts.

## Canonical architecture

Architecture authority: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

```text
OPERATOR COMMAND
  -> durable harness (idempotency + checkpoints)
  -> kernel activities
       compile_screenplay
       build_continuity_ledger
       compile_shot_contracts
  -> PipelineResult (non-canonical run record; IR/ledger/shots remain kernel truth)
```

Workflow run records are **not** canonical film state. They are execution provenance.

## Bounded sequence

1. Typed pipeline command schema (mutation contract fields)
2. In-process durable run store with idempotency keys
3. Checkpointed kernel pipeline executor
4. Temporal adapter contracts (workflow/activity names and payloads)
5. Read-only/query + start surfaces (REST, MCP, CLI)
6. Recovery tests (duplicate idempotency, resume-from-checkpoint semantics)
7. M3 validation receipt

## M3 exit gate

```yaml
pipeline_compile_ledger_shots: PASS
idempotent_replay: PASS
checkpoints_ordered: PASS
mutation_contract_fields_required: PASS
temporal_adapter_contracts_documented: PASS
rest_mcp_cli: PASS
ruff_mypy_pytest: PASS
```

## Authority rules

- Kernel outputs remain the only story-truth artifacts.
- Harness runs require actor, authorization scope, idempotency key, command version, rationale.
- Expected-state hash is required when continuing an existing logical document revision.
- No provider generation, media workers, or autonomous repair loops in M3.
- Temporal server is optional for unit tests; adapter contracts must remain stable.

## Explicit exclusions

- Image/video/voice generation
- Provider gateway execution
- Generator-evaluator repair loops
- Autonomous rewriting
- Full multi-tenant authN/Z
- PostgreSQL persistence (filesystem/in-memory run store only)

## Post-M3 continuation

```text
M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 CONTROLLED 30-60 SECOND PROOF
```
