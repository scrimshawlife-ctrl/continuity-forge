# CONTINUITY_FORGE_LONG_FORM_UX_001

## Intent

Campaign design for **long-form scale** on the operator surface and kernel
pipeline: navigate hundreds of scenes/shots without freezing the workbench,
invalidate and recompile only what changed, and stream honest
budget/provider/workflow telemetry while production remains non-claimed.

This is **Phase 4** of the audit-hardening campaign. It is **docs-first**:
acceptance criteria and contracts only. Full features are **not** implemented
in this campaign pass unless a stub is trivial and non-binding.

Parent workflow: [`CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001.md`](CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001.md)  
Architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)  
Agent contract: [`AGENTS.md`](../../AGENTS.md)  
UI baseline: [`CONTINUITY_FORGE_OPERATOR_UI_001.md`](CONTINUITY_FORGE_OPERATOR_UI_001.md)

**architecture_rewrite:** `NOT_REQUIRED` — extend existing Hallmark Terminal
workbench (`apps/web/`), harness checkpoints, and provider/proof receipts.
Do not migrate to React/Vue or invent a second film state store.

---

## Status

```text
campaign: CONTINUITY_FORGE_LONG_FORM_UX_001
phase: 4_long_form
mode: implemented
implementation: COMPLETE
architecture_rewrite: NOT_REQUIRED

# Prerequisite scoreboard (audit phases 1–3)
phase1_trust_boundary: REQUIRED   # envelope, lease, tenant, bootstrap
phase2_production_ci: REQUIRED    # packaging + integration skeleton
phase3_operator_ux: REQUIRED      # exec vs readiness, repair rationale

# This campaign (Phase 4)
long_form_campaign_doc: PASS
feature_implementation: COMPLETE  # all six long-form slices implemented with tests
slice_1_scene_shot_nav: IMPLEMENTED  # apps/web scene nav + filter + URL deep-link
slice_2_virtualized_tables: IMPLEMENTED  # virtual tbody + filters/sort + flag fallback
slice_3_dependency_invalidation: IMPLEMENTED  # pure graph + POST /v1/invalidation/preview + UI stale column
slice_4_incremental_compile: IMPLEMENTED  # compile_incremental + CLI/API/MCP + UI advanced + goldens
slice_5_budget_telemetry: IMPLEMENTED  # CostEvent/Ledger/Summary + proof emit + UI burn-down chips
slice_6_streaming_workflow: IMPLEMENTED  # poll GET .../events + UI progress + dual-lane copy
trivial_stubs: NONE
```

Update feature gates only when a later PR implements a slice with tests.
Do not mark scale features PASS from this document alone.

---

## Prerequisite: dependency on phases 1–3

Phase 4 **must not** ship scale UX that weakens authority, CI, or honesty
invariants established earlier.

| Phase | Campaign / surface | What long-form depends on |
|-------|--------------------|---------------------------|
| **1 Trust boundary** | `CONTINUITY_FORGE_AUTHORITY_HARDENING_001` | `MutationEnvelope` on canon writes; write-lease exclusivity; tenant-scoped keys; bootstrap fail-closed; PROPOSED ≠ canon |
| **2 Production CI** | packaging + integration workflows | Wheel install gate; Postgres/MinIO smoke skeleton; `make validate` remains the fast merge gate; no unpaid live provider calls in CI |
| **3 Operator UX** | `CONTINUITY_FORGE_OPERATOR_UI_001` (v1.3 + phase 3) | Dual-lane **execution success** vs **production readiness**; repair/validator rationale on shot rows; approval empty-state; claim `controlled_proof_not_production_ready` |

**Hard rule:** Long-form navigation and streaming must not rebrand proof
success as ACCEPTED film, hide the non-production claim, or write canon
outside envelope + lease.

---

## Authority rules (must not weaken)

| Rule | Implication for long-form |
|------|---------------------------|
| Source screenplay is immutable input | Incremental compile never rewrites source; only re-derives IR/ledger/shots |
| Deterministic kernel output is canon only after validation | Partial recompiles must re-validate affected artifacts; no “dirty but accepted” rows |
| Provider / model output is always `PROPOSED` until reviewed | Telemetry and stream events label candidates PROPOSED; never silent commit |
| Agents must not bypass command validation | Streaming progress is read-side; mutations still use envelope + lease |
| Checkpoints / chat / workflow scratch are never film state | Streamed workflow state is run provenance, not Production IR |
| Controlled proof is not production-ready | Scale UI retains dual-lane chips and claim banner |

---

## Current baseline (why this campaign exists)

Observed on the controlled-proof workbench (`apps/web/`):

- Proof receipt renders **all** shot rows via full DOM replace (`shotRows.replaceChildren` + loop).
- Scene/shot counts appear on project status; there is no hierarchical
  scene → shot navigator for long scripts.
- Compile/proof default is whole-document; incremental compile + invalidation preview are optional operator paths (not production film).
- Budget wall-clock remains on the proof receipt; cost ledger + provider traces
  are now run-scoped telemetry (mock fixed cost; not project canon).
- Harness stores ordered checkpoints on `WorkflowRun`; operators poll
  `GET /v1/pipeline/runs/{id}/events` for ordered progress (SSE deferred).

These are acceptable for short controlled proofs (30–60s mock path). They
do not scale to feature-length operator review.

---

## Work items

Each item below is a **design slice**. Implementation is deferred to later
PRs. Prefer PR-sized vertical slices that keep Hallmark Terminal tokens and
`make validate` green.

---

### 1. Scene / shot navigation

#### Problem

Operators cannot efficiently locate, filter, or jump between scenes and shots
once a project exceeds a handful of scenes. The workbench is receipt-centric:
after proof, shots appear as a flat table with no scene hierarchy, no deep
link, and no “focus this scene’s contracts / ledger facts” path. Long scripts
make review and lease-scoped edits operationally slow and error-prone.

#### Non-goal

- Multi-project studio dashboard or timeline NLE
- Visual storyboard scrubber or media player
- Autonomous “director jumps to next problem shot” agent
- Rewriting MCP/REST resource trees into a new resource model
- Frontend framework migration

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 1.1 | Scene list derived from Production IR `scenes` (or project status counts + resource fetches), ordered as in source |
| 1.2 | Selecting a scene filters or focuses the shot/contract list to that `scene_id` |
| 1.3 | URL or query param deep-link: `document_key` + optional `scene_id` / `shot_id` restores focus after reload |
| 1.4 | Keyboard: next/prev scene and next/prev shot without losing dual-lane claim banner |
| 1.5 | Empty / missing scene selection shows an explicit empty state (not a blank table) |
| 1.6 | Navigation is read-only; changing selection does not mutate canon or acquire leases |
| 1.7 | Existing short golden fixtures still render without requiring navigation chrome to be expanded |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Resource paths remain tenant-scoped; navigation never exposes cross-tenant projects |
| **2** | No new merge-required services; fixture-based unit/contract tests only |
| **3** | Scene focus must preserve execution-vs-readiness chips and repair-rationale columns when a receipt is present |

---

### 2. Virtualized tables

#### Problem

Receipt and status tables append one DOM row per shot. For long-form (hundreds
to thousands of contracts), full-table render blocks the main thread, balloons
memory, and makes scroll/search unusable. Phase 3 repair-rationale cells worsen
per-row cost.

#### Non-goal

- Replacing the Hallmark table aesthetic with a third-party data-grid product
  as a hard dependency for the default path
- Infinite-scroll over the network for canon (server paging may land later;
  first slice is client virtualization of an already-fetched or windowed list)
- Pixel-perfect spreadsheet editing of IR fields
- Virtualizing the raw JSON receipt dump (keep collapsible / capped)

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 2.1 | Shot/contract table renders only visible rows (+ small overscan); off-screen rows are not all mounted |
| 2.2 | With a synthetic fixture of ≥ 500 shot rows, initial paint and scroll remain interactive on a mid-tier laptop (document target: no multi-second main-thread freeze) |
| 2.3 | Column set still includes status, attempts, repair rationale summary, and candidate hash (Phase 3 fields) |
| 2.4 | Sort/filter (by status, scene, has-repair) works with virtualization without dropping rows from the logical dataset |
| 2.5 | Accessibility: keyboard focus and row announce remain usable for the focused row; not only mouse-hover |
| 2.6 | Fallback: if virtualization is disabled (feature flag), full table still works for short proofs |
| 2.7 | No claim that virtualization implies production film readiness |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Virtualization is presentation-only; no new write paths |
| **2** | Performance checks stay local/unit or optional smoke — not a paid-provider CI job |
| **3** | Virtual rows must still surface repair/validator rationale and dual-lane status chips |

---

### 3. Dependency-graph invalidation

#### Problem

Today, re-running compile/ledger/shots/proof is effectively whole-document.
Operators cannot see which downstream artifacts are **stale** after a scoped
source or ledger change. Without an explicit dependency graph, repair and
regeneration risk silent omission, over-invalidation, or keeping stale
PROPOSED media as if current.

#### Non-goal

- Full incremental video re-render pipeline
- Automatic regeneration of PROPOSED media without operator command + budget
- Graph database product or external DAG orchestrator replacing Temporal/harness
- Letting agents mark artifacts ACCEPTED via graph edges
- Inventing story content outside IR/ledger/shot compilers

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 3.1 | Documented dependency edges (minimum): `source_hash` → Production IR scenes/atoms → continuity ledger facts → shot contracts → (optional) PROPOSED candidates / proof receipt rows |
| 3.2 | Invalidation API or pure function: given a change set (e.g. scene_ids, entity_ids), return the set of artifact ids/hashes marked stale |
| 3.3 | Stale markers are visible in the UI (badge or column) without deleting prior hashes (lineage retained) |
| 3.4 | Recompute paths only refresh stale subgraph unless operator forces full rebuild |
| 3.5 | Invalidation never elevates PROPOSED → canon; regen remains gateway/repair scoped |
| 3.6 | Determinism: same inputs + change set → same stale set (golden unit tests) |
| 3.7 | Architecture edges: invalidation module does not import provider workers or write S3 bytes |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Any invalidation that records project-level dirty state uses envelope + lease; expected-state hash conflicts remain enforced |
| **2** | Unit tests for graph purity under `make validate`; no Temporal cluster required |
| **3** | Stale-artifact views align with Phase 3 “honest ops” UX (explicit stale vs ready; never hide claim banner) |

---

### 4. Incremental compile

#### Problem

Full recompile of feature-length Fountain/FDX is too slow for edit loops and
over-broadens provenance churn (`production_ir_hash`, ledger, shot contracts).
Operators need a **bounded** recompile that preserves stable ids for unchanged
regions and only re-emits affected scenes/atoms while keeping silent-omission
guards.

#### Non-goal

- Claiming feature-length production readiness
- Non-deterministic or model-assisted “smart” partial parse that skips schema
  validation
- In-place mutation of source text
- Dropping coverage accounting or provenance on partial runs
- Replacing M0 golden corpus gates with best-effort heuristics

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 4.1 | API/CLI surface (design): `compile --incremental` or equivalent with explicit `base_ir_hash` / `expected_state_hash` when continuing a project |
| 4.2 | Unchanged scenes retain stable `scene_id` / atom ids across incremental runs (reproducibility gate) |
| 4.3 | Changed scenes recompile with full schema validation; partial IR merges fail closed on invariant violation |
| 4.4 | Coverage accounting reports both recompiled and carried-forward regions (no silent omission of unchanged scenes) |
| 4.5 | Downstream invalidation (item 3) is invoked after incremental compile |
| 4.6 | Golden tests: minimal fixture full compile equals incremental compile with empty change set |
| 4.7 | Proof/claim path still emits `controlled_proof_not_production_ready` when proof is run on partial graphs |
| 4.8 | REST/MCP docs list incremental as optional; default remains full compile for short proofs |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Incremental compile that **ingests or updates project canon** requires MutationEnvelope + write lease + expected-state hash; dry compile-only may stay read-side |
| **2** | Incremental path covered by unit/golden tests in fast gate; integration optional |
| **3** | UI “Compile only” advanced action gains an incremental option only after dual-lane messaging for partial vs full results is clear |

---

### 5. Budget / provider telemetry

#### Problem

Proof receipts expose coarse wall-clock budget (`budget_seconds`,
`within_budget`, `elapsed_seconds`) and per-shot attempts, but not a live or
historical **cost ledger**: provider identity, model/seed provenance, token or
dollar estimates, retry spend, or campaign burn-down. Architecture already
lists required telemetry (`cost_ledger`, provider/seed provenance, model
request traces) that the operator UI does not surface.

#### Non-goal

- Live paid provider calls in CI
- Billing product / invoicing system
- Hiding costs behind “success” when over budget
- Letting budget telemetry auto-approve high-cost campaigns (approval thresholds
  remain human for high-cost generation)
- Replacing mock-default providers with always-on real APIs

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 5.1 | Telemetry schema (design): per-attempt records with `provider_id`, `model`, `seed` (if any), `latency_ms`, `estimated_cost` (nullable), `authority` (`PROPOSED`), links to candidate/artifact hash |
| 5.2 | Aggregate views: total estimated cost, count by provider, retry spend, wall-clock vs budget |
| 5.3 | UI panel or receipt section shows budget burn-down without implying production readiness |
| 5.4 | Over-budget state is a visible warn chip (alongside not-production-ready), not only a boolean field buried in JSON |
| 5.5 | Telemetry append-only for a run; corrections are new events, not silent edits |
| 5.6 | Mock providers emit synthetic zero/fixed-cost traces so UI and tests work offline |
| 5.7 | No provider module imports ProjectStore to “save cost as canon”; cost ledger is run/provenance scoped unless an approved commit path is explicitly designed later |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Cost events do not become project canon without envelope + approval path; PROPOSED boundary holds |
| **2** | Telemetry tests use mock providers; packaging/integration gates do not require live keys |
| **3** | Budget chips compose with execution-ok / not-production-ready dual lane (three-way honesty: exec · budget · readiness) |

---

### 6. Streaming workflow state

#### Problem

Durable harness runs accumulate checkpoints (`compile` → `ledger` → `shots`,
etc.), but the operator workbench only sees completed proof receipts or a
static run list. Long jobs give no progressive feedback, no mid-run failure
localization, and no way to distinguish **workflow progress** from **film
readiness**.

#### Non-goal

- Replacing Temporal (or the in-process harness) with ad-hoc websocket business
  logic that owns canon
- Streaming full IR blobs on every tick
- Chat-style agent token streaming as a substitute for checkpoint events
- Auto-resume UI that bypasses idempotency keys or leases
- Claiming streamed “100% complete” equals ACCEPTED production

#### Acceptance criteria

| # | Criterion |
|---|-----------|
| 6.1 | Event model (design): ordered workflow events — `run_started`, `checkpoint`, `provider_attempt`, `validation`, `run_completed`, `run_failed` — with `run_id`, timestamps, and non-canon payload refs |
| 6.2 | Transport options documented: SSE and/or poll `GET .../runs/{id}/events` (first implementation may be poll-only) |
| 6.3 | UI progress shows current checkpoint label + percent-or-step without replacing claim banner |
| 6.4 | On failure, last successful checkpoint and error code are visible; retry uses same idempotency key semantics as harness |
| 6.5 | Disconnect/reconnect: client can resume from `last_event_id` without duplicating canon writes |
| 6.6 | Stream payloads never include provider secrets or raw API keys |
| 6.7 | Explicit copy: “workflow complete” ≠ “production ready” (Phase 3 dual-lane preserved) |
| 6.8 | Unit tests for event ordering and idempotent replay of the same checkpoint sequence |

#### Dependency on phases 1–3

| Phase | Dependency |
|-------|------------|
| **1** | Stream is observability; mutations (cancel, re-queue) still require actor identity and, where applicable, lease/envelope |
| **2** | Stream/poll tests run without a live Temporal cluster (in-process harness fixtures); Temporal fleet remains non-production-validated |
| **3** | Progress UI must not collapse execution success into readiness; repair events should carry rationale hooks for the shot table |

---

## Explicit exclusions (campaign-wide)

- Feature-length readiness claims or marketing surfaces
- React/Vue/Svelte migration
- Autonomous director agent holding full screenplay memory
- Production-validated Temporal fleet requirement for Phase 4 design exit
- Live paid provider calls in CI
- Collapsing PROPOSED media into project canon from the UI
- Dual film-state stores (chat memory, agent scratch, or “UI draft canon”)
- Full implementation in this docs pass (unless a later PR opts into a
  **trivial stub** — see below)

---

## Implementation posture

| Mode | Allowed |
|------|---------|
| This campaign pass | Write/maintain this doc; optional cross-links from audit workflow / AGENTS |
| Trivial stubs only | e.g. a `# long-form (planned)` comment region, feature-flag constant defaulting off, or empty module docstring — **no** user-visible incomplete feature that implies scale readiness |
| Full features | Separate PR-sized slices after phases 1–3 remain green; each slice updates the scoreboard below |

Suggested future PR order (non-binding):

```text
1) dependency-graph invalidation — DONE
2) incremental compile — DONE
3) budget/provider telemetry schema — DONE
4) streaming/poll workflow events — DONE
5) scene/shot navigation + virtualized tables — DONE
```

Kernel-first keeps the UI honest: navigation and virtualization without
invalidation/incremental compile only paper over scale problems.

---

## Exit gates

### Campaign-doc exit (this pass)

```yaml
long_form_campaign_doc: PASS
items_covered:
  - scene_shot_navigation
  - virtualized_tables
  - dependency_graph_invalidation
  - incremental_compile
  - budget_provider_telemetry
  - streaming_workflow_state
per_item_fields: [problem, non_goal, acceptance_criteria, phase_1_3_dependency]
full_feature_implementation: NOT_REQUIRED
architecture_rewrite: NOT_REQUIRED
```

### Future implementation scoreboard (update only with tests)

```yaml
scene_shot_navigation: IMPLEMENTED
virtualized_tables: IMPLEMENTED
dependency_graph_invalidation: IMPLEMENTED
incremental_compile: IMPLEMENTED
budget_provider_telemetry: IMPLEMENTED
streaming_workflow_state: IMPLEMENTED
make_validate: local_gate_for_slices
```

---

## Risks

| Risk | Mitigation |
|------|------------|
| UI scale work ships before invalidation → stale green rows | Kernel-first PR order; stale badges required before bulk regen UI |
| Streaming confused with canon updates | Event schema marks provenance-only; AGENTS.md citation in API docs |
| Virtualization drops repair rationale | Acceptance 2.3 pins Phase 3 columns |
| Incremental compile silent omission | Coverage accounting + golden empty-changeset equality |
| Cost telemetry enables auto high-spend | Keep human approval thresholds for high-cost campaigns |
| Phase 4 used to reopen React migration | Explicit non-goal; Hallmark Terminal retained |

---

## Related campaigns

| Doc | Relation |
|-----|----------|
| `CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001` | Parent workflow; Phase 4 long-form |
| `CONTINUITY_FORGE_AUTHORITY_HARDENING_001` | Phase 1 trust boundary |
| `CONTINUITY_FORGE_OPERATOR_UI_001` | Phase 3 UX baseline to extend |
| `CONTINUITY_FORGE_COMPILER_FOUNDATION_001` | M0 full compile spine |
| `CONTINUITY_FORGE_DURABLE_HARNESS_001` | Checkpoints / run provenance |
| `CONTINUITY_FORGE_PROVIDER_GATEWAY_001` | PROPOSED-only workers |
| `CONTINUITY_FORGE_REPAIR_LOOP_001` | Repair attempts / rationale source |
| `CONTINUITY_FORGE_CONTROLLED_PROOF_001` | Non-production proof claim |

---

## Completion receipt (implementation)

- **slices:** 4.1–4.6 all IMPLEMENTED with unit/contract tests + `make validate`
- **PRs (indicative):** scene nav, virtualized tables, dependency invalidation,
  incremental compile, budget telemetry, workflow event poll
- **transport choice:** poll-first for workflow events (`GET .../events`); SSE deferred
- **virtualization choice:** client-side virtual tbody with filters (server paging deferred)
- **gates:** `make validate` green; claim banners and PROPOSED boundary retained
- **MCP close-out:** `get_pipeline_run_events` mirrors REST poll surface
- **explicit non-claims:** not production film; not production-validated Temporal fleet
- **next bounded action (outside this campaign):** production stack when operators
  need live providers / Temporal cluster / multi-tenant OAuth — still non-goals here
