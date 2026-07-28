# CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001

## Intent

Grok workflow encoding the Engineering + UI Audit recommendations as a
repeatable multi-agent campaign (plan or execute phases).

## Workflow

| Field | Value |
|-------|--------|
| Name | `cf-audit-hardening` |
| Path | `.grok/workflows/cf-audit-hardening.rhai` |
| Invoke | `/cf-audit-hardening` or `/workflow cf-audit-hardening` |

## Args

```json
{ "mode": "plan" }
{ "mode": "execute", "phase": "1" }
{ "mode": "execute", "phase": "all" }
{ "mode": "plan", "root": "/path/to/continuity-forge" }
```

| Arg | Default | Values |
|-----|---------|--------|
| `mode` | `plan` | `plan` · `execute` |
| `phase` | `1` | `1` · `2` · `3` · `4` · `all` (execute only) |
| `root` | repo hint string | optional path for agents |

## Phases (audit mapping)

1. **Trust boundary** — envelope, lease concurrency, tenant isolation, architecture edges
2. **Production CI** — wheel install, coverage floors, Postgres/MinIO integration skeleton
3. **Operator UX** — readiness vs success, repair evidence, honest docs
4. **Long-form** — campaign doc for scale features (minimal code)

## Agent budget (approximate)

| Path | Agents |
|------|--------|
| plan | 4 baseline + 1 synthesize ≈ **5** |
| execute phase 1 | plan path + 3 implement + 1 verify ≈ **9** |
| execute all | much higher; pauses between phases |

Recommend `agent_budget` ≥ 32 for execute-all.

## Smoke check

`validate_only: true` with `{ "mode": "plan" }` — compiles and walks plan path with canned host results only.

## Status

```text
workflow_authored: PASS
validate_only_plan: PASS
validate_only_execute_p1: PASS (canned)
live_run: optional
```
