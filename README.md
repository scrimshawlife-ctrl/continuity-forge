# Continuity Forge

**A deterministic script-to-production compiler for drift-resistant AI film generation.**

Continuity Forge converts a screenplay into a provenance-preserving Production IR, continuity ledger, scene graph, and eventually model-neutral shot manifests. Generative models may propose or render artifacts; they do not own canonical narrative state.

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

Video generation, visual-bible generation, and autonomous rewriting are explicitly excluded.

## Stack

- Python 3.12+
- Pydantic v2
- FastAPI
- PostgreSQL later; filesystem artifacts for M0
- TypeScript/Next.js operator surface later
- Temporal introduced after the deterministic compiler passes M0

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
SOURCE SCRIPT → DETERMINISTIC PARSER → VALIDATED PRODUCTION IR
                                     ↑
                        MODEL PROPOSALS REQUIRE REVIEW
```

Canonical state changes require schema validation, source provenance, and deterministic diagnostics.
