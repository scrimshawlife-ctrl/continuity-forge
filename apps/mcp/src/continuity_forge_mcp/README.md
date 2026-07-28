# MCP read-only compiler server

M0 exposes deterministic, non-persistent compiler queries over stdio using the official MCP Python SDK. No tool writes canonical state, files, databases, or workflow history.

## Run

```bash
continuity-forge-mcp
```

## Tools

- `compile_script`: compile supplied Fountain source into validated Production IR without persistence
- `get_compile_diagnostics`: return typed deterministic diagnostics
- `list_scenes`: return compact stable scene summaries
- `get_scene`: return one scene by stable identifier
- `audit_script_coverage`: return source-accounting totals and uncovered spans
- `build_ledger`: derive a deterministic continuity ledger from compiled source
- `list_entities`: list ledger entities (characters, locations, props, wardrobe, injury)
- `list_setup_payoff_links`: list setup/payoff links from the ledger
- `build_shot_contracts`: compile model-neutral shot contracts from source
- `list_shot_summaries`: compact per-scene shot summaries

All calls accept Fountain or Final Draft XML source text, a `format` selector, an optional `document_key`, and an optional `revision`. The key identifies the logical screenplay across revisions; when omitted, identity is derived from the source hash so unrelated untitled inputs do not collide. `revision` is preserved on the returned Production IR for provenance parity with REST. The server remains deliberately stateless. Durable project resources, authenticated mutation commands, approvals, and workflow integration remain later milestones.
