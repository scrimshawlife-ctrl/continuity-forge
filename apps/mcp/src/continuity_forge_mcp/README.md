# MCP Continuity Forge server

Stdio MCP server for Hermes/OpenClaw. No tool writes canonical film state without a mutation contract; generation returns `PROPOSED` candidates only.

## Run

```bash
continuity-forge-mcp
```

## Tool groups

### Kernel reads
- `compile_script`, `get_compile_diagnostics`, `list_scenes`, `get_scene`, `audit_script_coverage`
- `build_ledger`, `list_entities`, `list_setup_payoff_links`
- `build_shot_contracts`, `list_shot_summaries`

### Durable pipeline
- `run_kernel_pipeline`, `get_pipeline_run`, `get_temporal_manifest`

### Operator (M4)
- `acquire_write_lease`, `release_write_lease`, `ingest_script`
- `get_project_status`, `resolve_resource`, `audit_drift`
- `inspect_scene`, `inspect_character_state`, `list_pipeline_runs`

### Generation (M5/M6 mock)
- `queue_generation` — PROPOSED mock candidate
- `run_shot_repair_loop` — generate → validate → repair

Resources use `cf://projects/...`, `cf://scenes/...`, `cf://shots/...` via `resolve_resource`.
