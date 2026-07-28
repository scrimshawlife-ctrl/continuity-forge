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

`CONTINUITY_FORGE_CONTINUITY_LEDGER_001` — `M1_CONTINUITY_LEDGER`

M0 compiler spine is complete. Active work derives a deterministic continuity ledger from Production IR.

### M1 scope

- Entity registry (characters, locations, props, wardrobe, injury)
- Presence, enter/exit, holds/wears/injured facts with atom provenance
- Scene continuity contracts
- Setup/payoff linking
- Read-only REST (`POST /v1/continuity-ledger`) and MCP ledger tools

Video generation, visual-bible generation, durable Temporal workflows, shot contracts, and autonomous rewriting remain excluded.

## Planned progression

```text
M0 COMPILER SPINE (complete)
-> M1 CONTINUITY LEDGER (active)
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
make validate
python -m continuity_forge_compiler.cli compile tests/golden/fixtures/minimal.fountain --out out
python -m continuity_forge_compiler.cli compile tests/golden/fixtures/minimal.fdx --out out
continuity-forge-mcp
```

M0 supported grammar: [`docs/compiler/M0_SUPPORTED_GRAMMAR.md`](docs/compiler/M0_SUPPORTED_GRAMMAR.md)

Canonical local/CI gate: `python scripts/validate_m0.py` (also `make validate`).

## Authority rule

```text
SOURCE SCRIPT -> DETERMINISTIC PARSER -> VALIDATED PRODUCTION IR
                                         ^
                              MODEL PROPOSALS REQUIRE REVIEW
```

Canonical state changes require schema validation, source provenance, deterministic diagnostics, authorization, and an expected-state hash.

## Identity and provenance

`document_key` is the persistent logical identity of a screenplay. The source hash identifies a specific revision. Scene IDs derive from the document key plus normalized slugline occurrence, while atom IDs derive from typed normalized content within their scene. Unrelated insertions therefore preserve unaffected IDs. Ambiguous duplicate reconciliation across substantial edits remains a future revision-matching concern.

Every source line receives a contiguous `SourceSegment`. Narrative elements reference atoms, while blank lines and boneyard comments are explicit trivia. Successful accounting therefore reconstructs the complete source range with a coverage ratio of `1.0`.

## Diagnostic codes

- `CF100`: no scene headings found
- `CF101`: content before the first scene was retained in the preamble
- `CF102`: unclosed boneyard comment
- `FDX100`: malformed Final Draft XML
- `FDX101`: unsupported paragraph type retained as action
- `FDX102`: no scene headings found in the FDX document
- `FDX103`: pre-scene FDX content retained in the preamble

Diagnostics are deterministic compiler output. Documents containing error diagnostics are inspectable but must not be promoted to canonical state.
