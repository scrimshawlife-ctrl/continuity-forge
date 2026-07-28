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
- LangGraph, if used, is limited to bounded reasoning subgraphs and cannot own canonical state.

## Active campaign

Read `docs/campaigns/CONTINUITY_FORGE_DURABLE_HARNESS_001.md` before changing code.

M0–M2 kernel stages are complete. Active work is **M3 Durable Harness / Temporal adapter**.

## Scope discipline

Do not add generation providers, visual-bible systems, provider execution, or autonomous rewriting during M3 unless the active campaign is explicitly amended.

Do not implement a single autonomous director agent that carries the full screenplay as its private memory or sequentially generates scenes without canonical shot contracts and validation gates.

## Mutation contract

Any future mutating agent or MCP command must include:

- actor identity
- authorization scope
- idempotency key
- expected-state hash
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
