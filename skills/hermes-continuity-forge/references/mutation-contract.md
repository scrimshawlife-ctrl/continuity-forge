# Mutation contract & write leases

## Envelope fields (required on mutating paths)

| Field | Rule |
|-------|------|
| `actor_id` | Stable operator identity (Hermes session id ok) |
| `authorization_scope` | e.g. `kernel:pipeline`, `approvals`, `generation:repair` |
| `idempotency_key` | Unique per logical intent; retries reuse the same key |
| `rationale` | Why this mutation is happening (audit trail) |
| `expected_state_hash` | Required when updating existing project state |
| `command_schema_version` | Defaulted by models (e.g. `m4.operator.v1`) |

## Write lease

```text
acquire_write_lease(document_key, holder=actor_id, ttl_seconds=600)
  → mutate (ingest, approvals, …)
  → release_write_lease(document_key, holder=actor_id)
```

- Only the **holder** may mutate while the lease is active.
- Another actor receives a conflict error — surface it; do not spin forever.
- Always release on completion or failure when you acquired the lease.

## What needs a lease

- `ingest_script` (MCP)
- Approval request/decide (REST; actor must hold lease)
- Any future canon-writing tool

## What does not need a lease

- `compile_script`, ledger/shots builders on raw source
- `queue_generation` / `run_shot_repair_loop` (PROPOSED only; still no silent canon)
- Pure reads: status, resources, diagnostics

## Controlled proof

CLI / REST proof runners acquire and release leases internally. When assembling proof manually via MCP, mirror that: lease → ingest → per-shot repair → release.

## Forbidden

- Inventing a “save canon from chat” shortcut
- Reusing idempotency keys for different intents
- Mutating without rationale
- Claiming PROPOSED artifacts are final
