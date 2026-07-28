# CONTINUITY_FORGE_OPERATOR_UI_001

## Intent

Ship a technical/austere operator workbench for ops + producer overview: run controlled proof and read the receipt. Hallmark design (Workbench + Terminal). No production-film claims.

## Status

```text
operator_ui: PASS (v1.3 + phase 3)
proof_api: PASS
project_list: PASS
control_leases_approvals: PASS
static_mount: PASS
smoke: PASS (when API up)
phase3_exec_vs_readiness: PASS
phase3_repair_rationale: PASS
phase3_approval_empty: PASS
```

## Surface

| Piece | Location |
|-------|----------|
| UI | `apps/web/` |
| Tokens | `tokens.css`, `apps/web/tokens.css` |
| Hallmark log | `.hallmark/log.json` |
| API | `POST /v1/proof` → `ProofReceipt` |
| Canon | `GET /v1/projects`, `GET /v1/projects/{key}/status` |
| Serve | FastAPI static mount at `/` |
| Local | `make ui` → http://127.0.0.1:8080/ |

### v1.2 workbench actions

- Bootstrap dev key / whoami
- Compile only (no ingest)
- Export receipt JSON + copy receipt hash
- Load project status + list tenant projects

### v1.3 control surface

- Acquire / release / refresh write lease
- Request approval + grant/deny from list
- List pipeline runs for document key

### Phase 3 (no React migration)

- Separate **execution success** from **production readiness** after proof
- Prominently surface claim `controlled_proof_not_production_ready` on the receipt
- Shot rows show validator/repair rationale when `repair_actions` present
- Approval queue empty-state with clear next action (request approval + lease)
- Hallmark Terminal tokens retained (no reskin)

## Design fingerprint

- Genre: atmospheric
- Macrostructure: Workbench
- Theme: Terminal (dark · mono · phosphor)
- Nav: N8 Terminal command
- Footer: Ft4 Dense colophon
- Claim banner: `controlled_proof_not_production_ready`
- Post-proof dual lane: execution ok (chip--ok) · not production ready (chip--warn)

## Non-goals

- Real media generation UI
- Multi-project dashboard
- Temporal/admin chrome
- Marketing landing page
