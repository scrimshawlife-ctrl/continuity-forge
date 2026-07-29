# CONTINUITY_FORGE_PRODUCT_WORKFLOW_UI_001

## Objective

Transform Continuity Forge from an engineering-oriented proof workbench into a
clear creative-production application without weakening the deterministic kernel.

## Status

**Implemented on main (product shell + adapters + tests).** Not production-validated
live generation. Claim remains handoff / non-production film.

## Current-state audit (pre-change)

| Area | Before |
|------|--------|
| UI entry | Terminal-style nav: proof / results / advanced / status |
| Primary CTA | **Build breakdown** + peer **Run proof** |
| Language | IR, claim banners, backend chips, package hashes, leases |
| Persistence | Session + optional project store; browser-first workbench |
| API | Stable `/v1/breakdown`, compile, proof, leases, generate |
| Framework | Vanilla SPA `apps/web/` (index.html, app.js, styles.css) |

### Implementation map

| Concern | Location |
|---------|----------|
| Product view models | `packages/operator/.../product_workflow.py` |
| Product API adapters | `POST /v1/product/*` in `apps/api/.../main.py` |
| Creative UI | `apps/web/` (nav: Projects, Scenes, Continuity, Generate, Review, Export) |
| Kernel breakdown | Unchanged `cf.breakdown.v1` via `build_breakdown_from_text` |
| Developer surfaces | Settings → Developer (hashes, raw JSON, mock proof) |

## User workflow (shipped)

```text
Create Project → Import Script → Analyze Script → Review Scenes / Continuity
  → Resolve Conflicts → Prepare Scene for Generation → Export / Generate
  → Review decisions → (canon only via validated mutation paths)
```

## Architecture constraints (honored)

- Source script + operator approval remain authoritative.
- Models propose only; no silent canon mutation from UI display.
- Deterministic package hashes preserved for same input.
- Provenance labels: SCRIPT, INFERRED, USER_LOCKED, GENERATED, CONFLICT, STALE.
- Stable CLI / REST / MCP / proof / breakdown schemas kept; product routes are adapters.

## Phases

1. Audit + campaign skeleton — done
2. Product shell + Developer separation — done
3. Project create / import / analyze — done
4. Scenes + Continuity + conflicts + invalidation preview — done
5. Prepare scene package + export-only + review decisions — done
6. Tests + docs + validation — done

## Files changed (major)

- `packages/operator/src/continuity_forge_operator/product_workflow.py` (new)
- `packages/operator/src/continuity_forge_operator/__init__.py`
- `apps/api/src/continuity_forge_api/main.py` (product routes)
- `apps/web/index.html`, `app.js`, `styles.css`
- `tests/unit/test_product_workflow.py`
- `docs/PRODUCT_WORKFLOW.md`, `docs/architecture/OPERATOR_UI_ARCHITECTURE.md`
- `README.md`, `docs/HANDOFF.md`

## Decisions

- Stay on vanilla SPA (no framework rewrite) — lower risk to handoff path.
- Product packages live under operator package (adapters), not new kernel package.
- Browser `localStorage` for product project reopen + last-opened; server ingest/store unchanged for canon.
- Scene entry/exit UI is honest adapter over breakdown summaries (full ledger detail remains via existing endpoints / Developer raw JSON).
- Wardrobe/relationships only surface kernel-backed data; empty states when not extracted.

## Test evidence

```bash
make validate
make handoff
pytest tests/unit/test_product_workflow.py
```

## Screenshots

Capture via local `make ui` when a browser is available. Structural UI tests assert
nav labels and Analyze Script CTA in shipped HTML/JS.

## Remaining limitations

- No live provider generation in primary UI (export-only + mock proof under Developer).
- Scene merge/split boundary editing not full NLE — readiness + overrides only.
- Full emotional-state-by-scene / geography graphs not invented beyond kernel data.
- WCAG practical improvements shipped; no third-party audit lab.
- PDF/DOCX not supported (explicitly stated in UI).

## Final status

Campaign acceptance criteria for creative shell, analyze path, scenes/continuity/conflicts,
prepare/export, lineage-aware review intent, regression gates, and docs: **implemented**.
Production-validated film generation: **not claimed**.
