# Operator UI architecture

## Boundaries

```text
UI (apps/web)  →  Product API adapters (/v1/product/*)  →  Kernel builders
                 →  Stable contracts (/v1/breakdown, /v1/proof, …)
```

- **View models** live in `continuity_forge_operator.product_workflow`.
- **Canonical schemas** (`cf.breakdown.v1`, Production IR, ledger, shot contracts) are unchanged.
- **UI never writes film canon** from display actions. Overrides and review decisions are recorded as product metadata / intent; canon advancement uses `MutationEnvelope` + project store paths.

## Frontend state

Vanilla SPA (`index.html`, `app.js`, `styles.css`, `tokens.css`).

- Product projects: `localStorage` key `cf.product.projects.v1` + last-opened key.
- In-memory current project holds script text, analysis summary, scenes, entities, breakdown JSON, scene package, overrides, resolved conflict ids, review decisions.
- Server `ProjectStore` remains available via existing ingest/list endpoints for production-shaped backends.

## Persistence

| Layer | Role |
|-------|------|
| Runtime project store | **Source of truth** — ingest script, IR, product_meta (overrides, phase, review) |
| `GET /v1/product/projects` | Server project list (logical document keys) |
| `GET /v1/product/projects/{id}` | Hydrate script + product_meta for UI reopen |
| Browser localStorage | **Cache only** — last-opened key + offline fallback |

No second persistence framework.

## Mutation rules

1. Analyze / breakdown / prepare = **read-side** (or pure compile).
2. Operator override preview returns USER_LOCKED draft + invalidation; apply stores override in product meta and marks STALE — does not rewrite kernel package in place without re-analyze.
3. Conflict resolve requires explicit `choice_id`.
4. Review accept sets `advances_canon` intent only; note in API response that validated mutation paths are required for true canon write.

## Dependency invalidation

`apply_operator_override` computes affected scenes/shots from package mentions. UI shows confirmation dialog before applying lock. Stale artifacts are not deleted.

## Provider adapter boundary

`SceneGenerationPackage` (`cf.scene_package.v1`) is provider-neutral. No `openai_payload` / `runway_payload` in core package. Provider-specific mapping stays in `continuity_forge_providers` when generation is configured.

## Accessibility approach

Semantic landmarks, skip link, focus-visible, button labels, alert live regions, badges with text (not color alone), mobile nav targets ≥ 44px height, `prefers-reduced-motion`.
