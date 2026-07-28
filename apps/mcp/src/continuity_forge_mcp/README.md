# MCP Continuity Forge server

Stdio MCP server for **Hermes** (preferred) and OpenClaw. No tool writes canonical film state without a mutation contract; generation returns **PROPOSED** candidates only.

## Install

From repo root (venv activated):

```bash
pip install -e '.[dev]'
which continuity-forge-mcp
```

## Run

```bash
continuity-forge-mcp
```

Hermes config must use an **absolute path** to this binary. Example:

[`docs/hermes/mcp.example.json`](../../../../docs/hermes/mcp.example.json)

Optional env (also set in MCP config `env`):

```bash
export CF_STORE_ROOT=/path/to/durable
export CF_PROVIDER=mock
```

## Hermes skill

Operator playbooks and authority rules ship as:

[`skills/hermes-continuity-forge/SKILL.md`](../../../../skills/hermes-continuity-forge/SKILL.md)

Integration guide: [`docs/hermes/README.md`](../../../../docs/hermes/README.md).

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

### Generation (M5/M6)
- `queue_generation` — PROPOSED candidate
- `run_shot_repair_loop` — generate → validate → repair

Resources use `cf://projects/...`, `cf://scenes/...`, `cf://shots/...` via `resolve_resource`.

Full argument reference: [`skills/hermes-continuity-forge/references/mcp-tools.md`](../../../../skills/hermes-continuity-forge/references/mcp-tools.md).

## Controlled proof

One-shot receipt is easier via REST `POST /v1/proof` or CLI `continuity-forge proof`. MCP can compose lease → ingest → per-shot repair for the same path.
