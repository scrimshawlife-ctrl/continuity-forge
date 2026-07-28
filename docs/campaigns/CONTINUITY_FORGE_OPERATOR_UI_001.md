# CONTINUITY_FORGE_OPERATOR_UI_001

## Intent

Ship a technical/austere operator workbench for ops + producer overview: run controlled proof and read the receipt. Hallmark design (Workbench + Terminal). No production-film claims.

## Status

```text
operator_ui: PASS
proof_api: PASS
static_mount: PASS
smoke: PASS (when API up)
```

## Surface

| Piece | Location |
|-------|----------|
| UI | `apps/web/` |
| Tokens | `tokens.css`, `apps/web/tokens.css` |
| Hallmark log | `.hallmark/log.json` |
| API | `POST /v1/proof` → `ProofReceipt` |
| Serve | FastAPI static mount at `/` |
| Local | `make ui` → http://127.0.0.1:8080/ |

## Design fingerprint

- Genre: atmospheric
- Macrostructure: Workbench
- Theme: Terminal (dark · mono · phosphor)
- Nav: N8 Terminal command
- Footer: Ft4 Dense colophon
- Claim banner: `controlled_proof_not_production_ready`

## Non-goals

- Real media generation UI
- Multi-project dashboard
- Temporal/admin chrome
- Marketing landing page
