# Continuity Forge MCP Surface

The M0 MCP package is a **read-only adapter over the deterministic compiler**.

It does not own canonical state, persistence, workflow execution, provider credentials, or artifact generation. A future MCP transport SDK must wrap the protocol-neutral registry in `continuity_forge_mcp.server` rather than reimplementing compiler behavior.

## Exposed tools

| Tool | Purpose | Mutates state |
|---|---|---|
| `cf.get_compile_diagnostics` | Return typed compiler diagnostics | No |
| `cf.audit_script_coverage` | Return source-coverage metrics | No |
| `cf.list_scenes` | Return stable scene summaries | No |
| `cf.inspect_scene` | Return one scene and its atoms | No |

## Authority rules

- Every tool recompiles from immutable supplied source.
- Stable IDs originate in the deterministic compiler.
- Unknown tools and scene IDs fail closed.
- No tool may write to a database, filesystem, project ledger, or provider API during M0.
- Hermes and OpenClaw are clients of this surface, not authority holders.

## Deferred until later milestones

- MCP transport/server SDK integration
- Project persistence and resource URIs
- Write leases and idempotent command envelopes
- Approval-gated mutation tools
- Temporal workflow commands
- Media-generation workers
