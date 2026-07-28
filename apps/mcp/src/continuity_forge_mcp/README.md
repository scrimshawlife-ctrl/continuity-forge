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

All calls accept Fountain or Final Draft XML source text, a `format` selector, and an optional `document_key`. The key identifies the logical screenplay across revisions. The server is deliberately stateless in M0. Durable project resources, authenticated mutation commands, approvals, and workflow integration remain later milestones.
