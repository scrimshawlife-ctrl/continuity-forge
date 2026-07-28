# Agent operating contract

## Authority

- Source screenplay text is immutable input.
- Deterministic parser output is canonical only after schema validation.
- Frontier-model output is always `PROPOSED` until reviewed and committed.
- Agents must not write directly to persistence or bypass command validation.
- Agent checkpoints, chat memory, and workflow scratch state are never canonical film state.

## Canonical architecture

Read `docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md` before changing system boundaries.

Continuity Forge is a deterministic cinematic-production kernel surrounded by a model-agnostic orchestration harness.

- Models generate proposals and media.
- Continuity Forge owns identity, memory, causality, continuity, approvals, validation, and provenance.
- Temporal owns durable workflow execution after M0.
- Hermes and OpenClaw are external operator clients through MCP and REST.
- Hermes must load `skills/hermes-continuity-forge` (or equivalent) and use MCP tools; it never stores film canon in chat memory.
- LangGraph, if used, is limited to bounded reasoning subgraphs and cannot own canonical state.

## Active campaign

M0–M7 controlled-proof path is complete. Prefer campaign docs under `docs/campaigns/` for residual work.

Post-proof foundations (providers, Temporal, Postgres/S3, multi-tenant auth, runtime wiring)
and operator UI v1.3 are on `main`.

Operator UI: `apps/web/` (Hallmark Terminal · Workbench). Served from the API at `/`.
Default UX: script → Run proof → receipt. Advanced: leases, approvals, runs, connection.

Hermes skill (agentic operator): `skills/hermes-continuity-forge/`.
Install + MCP wiring: `docs/hermes/README.md`.
Meta-prompt to rebuild the skill when tools change: `docs/hermes/BUILD_SKILL_PROMPT.md`.
Setup: `docs/SETUP.md`.

## CI

GitHub Actions workflow `.github/workflows/ci.yml` runs `python scripts/validate_m0.py`
(ruff, format, mypy, pytest). That is the merge gate. Local equivalent: `make validate`.

## Scope discipline

Do not claim feature-length readiness. Controlled proof uses mock workers only.

Do not implement a single autonomous director agent that carries the full screenplay as its private memory or sequentially generates scenes without canonical shot contracts and validation gates.

## Mutation contract

Any mutating agent or MCP command must include:

- actor identity
- authorization scope
- idempotency key
- expected-state hash (when continuing prior state)
- command schema version
- rationale

## Completion receipt

Every implementation pass must report:

- files changed
- tests added or updated
- commands executed
- passing/failing gates
- unresolved ambiguity
- next bounded action
