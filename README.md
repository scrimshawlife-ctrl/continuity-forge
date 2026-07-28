# Continuity Forge

**A deterministic cinematic-production kernel and model-agnostic harness for drift-resistant AI film generation.**

Continuity Forge converts a screenplay into a provenance-preserving Production IR, continuity ledger, scene graph, and model-neutral shot contracts. Generative models may propose or render artifacts; they do not own canonical narrative state.

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.

## Architecture

Continuity Forge is structured as three layers:

1. **Deterministic kernel** — screenplay, Production IR, continuity state, invariants, approvals, artifact lineage, and revision impact.
2. **Durable production harness** — retries, long-running generation, human approval waits, provider outages, cancellation, and recovery through Temporal after M0.
3. **Bounded agentic reasoning** — model-assisted interpretation, planning, evaluation, diagnosis, and repair proposals with no direct canonical authority.

Canonical architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

## Active campaign

`CONTINUITY_FORGE_COMPILER_FOUNDATION_001` — `M0_COMPILER_SPINE`

### M0 scope

- Script ingestion and source hashing
- Scene, action, and dialogue parsing
- Narrative atom generation
- Stable deterministic identifiers
- Production IR serialization
- Typed compile diagnostics
- Script coverage accounting
- Read-only REST and MCP surfaces

Video generation, visual-bible generation, durable Temporal workflows, and autonomous rewriting are explicitly excluded from M0.

## Planned progression

```text
M0 COMPILER SPINE
-> M1 CONTINUITY LEDGER
-> M2 SHOT CONTRACT COMPILER
-> M3 DURABLE HARNESS / TEMPORAL
-> M4 MCP OPERATOR SURFACE
-> M5 PROVIDER GATEWAY + ISOLATED WORKERS
-> M6 GENERATOR-EVALUATOR REPAIR LOOP
-> M7 30-60 SECOND CONTROLLED PROOF
```

## Stack

- Python 3.12+
- Pydantic v2
- FastAPI
- PostgreSQL later; filesystem artifacts for M0
- TypeScript/Next.js operator surface later
- Temporal introduced after the deterministic compiler passes M0
- MCP for Hermes, OpenClaw, and other operator clients
- Optional LangGraph only for bounded reasoning subgraphs

## Bootstrap

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
python -m continuity_forge_compiler.cli compile tests/golden/fixtures/minimal.fountain --out out
```

## Authority rule

```text
SOURCE SCRIPT -> DETERMINISTIC PARSER -> VALIDATED PRODUCTION IR
                                         ^
                              MODEL PROPOSALS REQUIRE REVIEW
```

Canonical state changes require schema validation, source provenance, deterministic diagnostics, authorization, and an expected-state hash.
