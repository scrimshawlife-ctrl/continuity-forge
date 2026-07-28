# MCP tool inventory (`continuity-forge-mcp`)

Source of truth: `apps/mcp/src/continuity_forge_mcp/server.py`.

## Kernel reads (no lease)

| Tool | Purpose |
|------|---------|
| `compile_script` | Fountain/FDX → Production IR JSON |
| `get_compile_diagnostics` | Diagnostics only |
| `list_scenes` | Scene id / ordinal / slugline |
| `get_scene` | One scene by `scene_id` |
| `audit_script_coverage` | Coverage report |
| `build_ledger` | Continuity ledger from source |
| `list_entities` | Ledger entities |
| `list_setup_payoff_links` | Setup/payoff links |
| `build_shot_contracts` | Shot contract bundle |
| `list_shot_summaries` | Compact shot list |

Common args: `source`, `title`, `document_key`, `format` (`fountain`|`fdx`), `revision`.

## Durable pipeline

| Tool | Purpose |
|------|---------|
| `run_kernel_pipeline` | Run kernel pipeline command (mutation-style fields on command) |
| `get_pipeline_run` | Fetch run by `run_id` |
| `get_temporal_manifest` | Temporal registration contracts |

## Operator (lease + project)

| Tool | Purpose |
|------|---------|
| `acquire_write_lease` | `document_key`, `holder`, `scope`, `ttl_seconds` |
| `release_write_lease` | `document_key`, `holder` |
| `ingest_script` | Lease-gated ingest + pipeline store |
| `get_project_status` | Status resource |
| `resolve_resource` | `cf://…` URI |
| `audit_drift` | CL2* diagnostics from stored ledger |
| `inspect_scene` | Scene manifest |
| `inspect_character_state` | Character entity + facts |
| `list_pipeline_runs` | Runs for document |

### `ingest_script` required mutation fields

- `source`, `document_key`, `actor_id`, `authorization_scope`, `idempotency_key`, `rationale`
- optional: `title`, `revision`, `format`, `expected_state_hash`

## Generation (mock / PROPOSED)

| Tool | Purpose |
|------|---------|
| `queue_generation` | One PROPOSED candidate for `shot_id` |
| `run_shot_repair_loop` | generate → validate → repair; `fail_first` forces first-shot repair demo |

Args: `document_key`, `shot_id`, `seed`, optional `max_attempts`, `fail_first`.
Also carry MutationEnvelope audit fields (defaults provided): `actor_id`,
`authorization_scope`, `idempotency_key`, `rationale`. Output remains PROPOSED.

## Resources (`resolve_resource`)

Examples:

- `cf://projects/{document_key}/status`
- `cf://projects/{document_key}/script`
- `cf://projects/{document_key}/production-ir`
- `cf://projects/{document_key}/continuity-ledger`
- `cf://scenes/{scene_id}/manifest`
- `cf://shots/{shot_id}/validation`

## REST complements (not MCP)

- `POST /v1/proof` — controlled proof receipt in one call
- `POST /v1/approvals/request` · `POST /v1/approvals/decide`
- `GET /v1/projects` · `GET /v1/projects/{key}/runs`
