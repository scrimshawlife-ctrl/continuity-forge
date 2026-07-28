# ADR-0001: Adopt a deterministic production harness

- Status: Accepted
- Date: 2026-07-28

## Context

Continuity Forge must coordinate multiple reasoning and media-generation systems across long-running scene workflows without allowing any model to own canonical story state.

A single autonomous director agent would reproduce context loss, narrative compression, visual drift, weak provenance, and uncontrolled revision cascades.

## Decision

Adopt a deterministic cinematic-production kernel surrounded by a model-agnostic orchestration harness.

- PostgreSQL and typed Python services own canonical state.
- Temporal will own durable production workflows after M0.
- MCP and authenticated REST expose controlled operator surfaces.
- Hermes is the preferred operator agent; OpenClaw is an alternate client.
- Frontier models and optional LangGraph subgraphs operate with proposal-only authority.
- Image, video, voice, lip-sync, FFmpeg, and validation functions run as isolated workers.

## Consequences

### Positive

- Providers and models remain replaceable.
- Workflow failure does not corrupt canonical state.
- Human approvals can pause and resume durably.
- Every artifact and decision can be traced to source state and commands.
- Agent reasoning can evolve without rewriting the core production system.

### Cost

- More explicit schemas, events, adapters, and validation gates are required.
- Creative generation cannot bypass approval and continuity contracts.
- Durable orchestration is deferred until the deterministic compiler foundation is stable.

## Invariant

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.
