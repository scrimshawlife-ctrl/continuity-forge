# CONTINUITY_FORGE_AUTHORITY_HARDENING_001

## Goal

Make Continuity Forge **authority invariants executable** (Phase 1 / trust
boundary of the audit-hardening campaign). Mutation contract, write-lease
concurrency, tenant isolation, and bootstrap-route safety become machine-enforced
via runtime guards + tests—not docs-only.

Parent workflow: [`CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001.md`](CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001.md)  
Architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)  
Agent contract: [`AGENTS.md`](../../AGENTS.md)  
Mutation reference: [`skills/hermes-continuity-forge/references/mutation-contract.md`](../../skills/hermes-continuity-forge/references/mutation-contract.md)

**architecture_rewrite:** `NOT_REQUIRED` — harden existing kernel, stores, and
API/MCP surfaces; do not invent a parallel authority framework.

---

## Authority rules (must not weaken)

These rules are **fixed** for this campaign. Implementation may tighten
enforcement; it must not dilute them.

| Rule | Source | Hardening implication |
|------|--------|------------------------|
| Source screenplay text is immutable input | `AGENTS.md` | Ingest stores source hash; no silent rewrite of source as model output |
| Deterministic parser output is canonical only after schema validation | `AGENTS.md` | Kernel IR/ledger/shots remain truth; harness runs are provenance only |
| Frontier-model / provider output is always `PROPOSED` until reviewed and committed | `AGENTS.md` | Generation + repair stay non-canon; may carry envelope fields for audit only |
| Agents must not write directly to persistence or bypass command validation | `AGENTS.md` | All project-canon writes go through `MutationEnvelope` + store/API gates |
| Agent checkpoints, chat memory, workflow scratch are never canonical film state | `AGENTS.md` | No “save canon from chat” path; MCP trusted-local does not elevate PROPOSED |
| Generation tools do **not** become silent canon writers | mutation contract | `queue_generation` / `run_shot_repair_loop` / preview remain PROPOSED |
| Controlled proof is not production-ready | UI / proof claim | Do not rebrand proof success as ACCEPTED film state |

**Forbidden under this campaign**

- Claiming PROPOSED artifacts are final or ACCEPTED project canon
- Removing or bypassing envelope fields on ingest / approvals / other canon writes
- Allowing open bootstrap-dev or wildcard anonymous mutations in production-shaped config
- Collapsing operator (`m4.operator.v1`) and pipeline (`m3.pipeline.v1`) schema versions
- Treating generation/preview as project-canon mutation “for convenience”

---

## Mutation contract (AGENTS.md alignment)

Any **mutating** agent, REST, or MCP command that writes project canon or
pipeline command provenance **must** include:

| Field | Role |
|-------|------|
| `actor_id` | Stable operator identity |
| `authorization_scope` | e.g. `kernel:pipeline`, `approvals`, `generation:repair` |
| `idempotency_key` | Unique per logical intent; retries reuse the same key |
| `expected_state_hash` | Required **when continuing prior project state** (project `state_hash` domain) |
| `command_schema_version` | Operator default `m4.operator.v1` (pipeline keeps its own version) |
| `rationale` | Audit trail; non-empty |

Canonical type: `MutationEnvelope` in
`packages/operator/src/continuity_forge_operator/models.py`.

```text
acquire_write_lease(document_key, holder=actor_id)
  → mutate under MutationEnvelope (+ expected_state_hash when continuing)
  → release_write_lease(document_key, holder=actor_id)
```

**Canon paths (envelope + active lease required)**

- `ProjectStore.ingest_script`, `request_approval`, `record_approval`
- REST: `/v1/projects/ingest`, `/v1/approvals/*` (and lease acquire for holders)
- MCP: `ingest_script` (and any future canon-writing tool)

**Non-canon paths (PROPOSED only; no project-canon write)**

- `queue_generation` / `run_shot_repair_loop` / generate preview
- Pure reads: status, resources, diagnostics, compile/ledger without ingest

Envelope fields on generation are for **audit continuity only** and must not
elevate authority from `PROPOSED`.

**Hash domains (do not confuse)**

| Token | Domain |
|-------|--------|
| `MutationEnvelope.expected_state_hash` | `ProjectRecord.state_hash` / project concurrency |
| `PipelineCommand.expected_state_hash` | Prior pipeline `shot_contracts_hash` (separate) |

---

## Phase 1 scope

1. **Envelope** — universal write contract on canon paths; schema validation
2. **Lease concurrency** — exclusivity, TTL, wrong-holder, race winner = 1
3. **Tenant isolation** — `tenant_id::document_key`; cross-tenant deny
4. **Bootstrap safety** — dev bootstrap fail-closed outside explicit local allow

Supporting slices (same phase, not separate product): architecture import edges,
expected-state conflict tests, approval transition regressions—document under
exit gate extensions when those tests land.

---

## Exit gates

Phase 1 **acceptance** requires all of the following gates green under the Fast
merge path (`make validate` / `python scripts/validate_m0.py`).

### Gate summary

```yaml
# Phase 1 — Trust boundary / authority hardening
envelope:                 # criteria below; PASS only when tests + runtime match
lease_concurrency:        # criteria below
tenant_isolation:         # criteria below
bootstrap_safety:         # criteria below
proposed_canon_boundary: PASS   # must remain PASS; never weaken
mutation_contract_aligned: PASS # AGENTS.md fields enforced on canon writes
make_validate:            # sole required local completion command
```

### 1. Envelope

**Intent:** Every project-canon write constructs or accepts a validated
`MutationEnvelope`. Incomplete envelopes fail at the boundary.

| Criterion | Evidence |
|-----------|----------|
| Required fields present and non-empty: `actor_id`, `authorization_scope`, `idempotency_key`, `rationale` | Pydantic `min_length=1` + contract rejects |
| Operator schema version fixed/allow-listed (default `m4.operator.v1`) | Validation boundary; invalid version fails closed |
| `expected_state_hash` when provided must match project `state_hash` (mismatch → conflict / 409-class) | Operator unit + ingest contract |
| API ingest + approvals + MCP ingest reject incomplete envelopes | `tests/contract/test_api.py`, MCP contracts |
| Pipeline run start validates shared write-contract fields via envelope (pipeline keeps its own command version) | API adapter uses `MutationEnvelope.from_parts` |
| Generation/preview remains PROPOSED; envelope optional-for-audit only, **no ProjectStore canon write** | Handler comments + authority assertions |

**PASS when:** unit + contract tests cover missing fields / invalid envelope;
canon handlers cannot complete without envelope; PROPOSED paths do not claim
canon.

### 2. Lease concurrency

**Intent:** At most one active write holder per document; TTL and races behave
deterministically.

| Criterion | Evidence |
|-----------|----------|
| Mutation without active lease fails | `test_ingest_requires_lease_and_stores_artifacts` |
| Second holder cannot acquire while first holds active lease | `test_write_lease_blocks_other_actor` |
| Wrong-holder `release_lease` fails | Operator unit |
| Expired lease → mutation rejected until re-acquire | Operator unit (TTL matrix) |
| Expired lease → new holder may acquire | Operator unit |
| Same-holder re-acquire / refresh behavior documented + tested | Operator unit |
| Concurrent acquirers → exactly one winner | Thread race unit (deterministic) |
| Existing API lease contract tests remain green | Contract suite |

**PASS when:** TTL lifecycle + exclusivity + race matrix green under
`make validate`.

### 3. Tenant isolation

**Intent:** Principals cannot read or mutate another tenant’s project by key
alone. Storage keys are tenant-scoped.

| Criterion | Evidence |
|-----------|----------|
| Storage key form `tenant_id::document_key` via `tenant_document_key` | `tests/unit/test_auth.py` |
| Spoofed foreign scoped keys re-scope under caller; never open peer namespace | unit + contract |
| Tenant A write; Tenant B status/get on same logical key → 404 / empty | `tests/contract/test_auth_api.py` |
| Tenant B write creates separate project; does not clobber A | contract isolation test |
| List endpoints tenant-filtered | contract |
| With auth required, missing credentials → 401 on protected routes | contract |
| Scope check: principal without required scope fails (when `require_scope` wired) | `tests/unit/test_auth.py` |

**PASS when:** cross-tenant read/write isolation and key spoof tests green;
auth-required path rejects unauthenticated callers.

### 4. Bootstrap safety

**Intent:** Dev tenant bootstrap cannot be abused in production-shaped config.

| Criterion | Evidence |
|-----------|----------|
| `POST /v1/tenants/bootstrap-dev` disabled unless `CF_BOOTSTRAP_DEV_TENANT` truthy | `bootstrap_dev_allowed` + contract 403 |
| Always disabled when `CF_ENV` / `ENVIRONMENT` is `production` or `prod` (even if flag set) | unit + contract |
| Flag-enabled local path returns dev tenant + key | contract happy path |
| Runtime auto-seed of dev tenant only when bootstrap allowed | `continuity_forge_runtime.factory` |
| Deploy/docs warn: never enable bootstrap in production | `docs/SETUP.md`, `deploy/README.md` |

**PASS when:** off-by-default + production force-deny + explicit local enable
are tested; network route cannot issue keys without the gate.

### 5. PROPOSED / canon boundary (non-regression)

| Criterion | Evidence |
|-----------|----------|
| Repair/proof candidates remain `Authority.PROPOSED` (or REJECTED); not ACCEPTED project canon | repair/provider tests |
| API generate / repair-loop responses expose PROPOSED authority | contract preview |
| Controlled-proof claim stays non-production-ready | UI / proof receipt |

**PASS when:** no path elevates mock/provider media to project canon without
explicit human approval + lease + envelope on an approvals/commit surface.

---

## Test map (Phase 1)

| Area | Primary paths |
|------|----------------|
| Envelope + lease | `tests/unit/test_operator.py`, `tests/contract/test_api.py`, `tests/contract/test_mcp.py` |
| Tenant + bootstrap | `tests/unit/test_auth.py`, `tests/contract/test_auth_api.py` |
| Architecture edges (supporting) | `tests/unit/test_architecture_edges.py` (or equivalent when added) |
| Harness expected-state (supporting) | `tests/unit/test_harness.py` |
| Local gate | `make validate` |

Suggested verify command (workflow Phase 1):

```bash
python -m pytest \
  tests/unit/test_operator.py \
  tests/unit/test_auth.py \
  tests/contract/test_api.py \
  tests/contract/test_auth_api.py \
  -q
```

Full acceptance still requires full Fast gate green.

---

## Explicit exclusions (Phase 1)

- Production PostgreSQL/S3 as merge-required (Phase 2 skeleton landed:
  `ci-integration.yml` + `tests/integration/test_postgres_minio_smoke.py`;
  not yet policy-required for everyday merge)
- Wheel-install / docker smoke CI (Phase 2 packaging: `ci-packaging.yml`)
- Full OAuth / IdP for MCP (MCP remains trusted-local unless a small shared secret already exists)
- Frontend framework migration or dual-lane UI (Phase 3)
- Checkpoint step-level Temporal resume rewrite
- Broadening generation tools into canon writers

---

## Status

```text
campaign: CONTINUITY_FORGE_AUTHORITY_HARDENING_001
phase: 1_trust_boundary
architecture_rewrite: NOT_REQUIRED

# Exit gate scoreboard — update to PASS only with test evidence
envelope: PENDING
lease_concurrency: PENDING
tenant_isolation: PENDING
bootstrap_safety: PENDING
proposed_canon_boundary: PASS   # baseline invariant; do not regress
mutation_contract_aligned: PASS # AGENTS.md contract documented + enforced on canon APIs
make_validate: PENDING
```

Update each gate to `PASS` when the corresponding criteria above are proven
green on `main` (or the integrating PR). Do not mark envelope/lease/tenant/
bootstrap PASS by documentation alone.

---

## Completion receipt (when Phase 1 closes)

Report:

- files changed
- tests added or updated
- commands executed
- passing/failing gates (table above)
- unresolved ambiguity
- next bounded action (Phase 2 production CI, or residual Phase 1 slices)

---

## Related campaigns

| Doc | Relation |
|-----|----------|
| `CONTINUITY_FORGE_AUDIT_HARDENING_WORKFLOW_001` | Workflow encoding; Phase 1 execute path |
| `CONTINUITY_FORGE_MCP_OPERATOR_001` | Original mutation_contract + write_lease surface |
| `CONTINUITY_FORGE_DURABLE_HARNESS_001` | Pipeline mutation fields / idempotency |
| `CONTINUITY_FORGE_PROVIDER_GATEWAY_001` | PROPOSED-only workers |
| `CONTINUITY_FORGE_CONTROLLED_PROOF_001` | Non-production-ready proof claim |
