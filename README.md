# Continuity Forge

**A deterministic cinematic-production kernel and model-agnostic harness for drift-resistant AI film generation.**

Continuity Forge converts a screenplay into a provenance-preserving Production IR, continuity ledger, scene graph, and model-neutral shot contracts. Generative models may propose or render artifacts; they do not own canonical narrative state.

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.

## Architecture

1. **Deterministic kernel** — screenplay, Production IR, continuity state, invariants, approvals, artifact lineage.
2. **Durable production harness** — pipeline commands, idempotency, checkpoints, Temporal adapter contracts.
3. **Operator surface** — project store, write leases, MCP/REST resources and tools.
4. **Mock provider gateway + repair loop** — PROPOSED candidates only; deterministic validate/repair.
5. **Controlled proof** — end-to-end mock path on a golden continuity fixture.

Canonical architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

## Milestone status

```text
M0 COMPILER SPINE .................... complete
M1 CONTINUITY LEDGER ................. complete
M2 SHOT CONTRACT COMPILER ............ complete
M3 DURABLE HARNESS / TEMPORAL ........ complete (in-process + adapter contracts)
M4 MCP OPERATOR SURFACE .............. complete
M5 PROVIDER GATEWAY + WORKERS ........ complete (mock only)
M6 GENERATOR-EVALUATOR REPAIR LOOP ... complete (mock only)
M7 CONTROLLED 30-60s PROOF ........... complete (mock media; not production-ready film)
```

## Bootstrap

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
make validate
make proof
```

Useful commands:

```bash
continuity-forge compile tests/golden/fixtures/minimal.fountain --out out
continuity-forge ledger tests/golden/fixtures/continuity.fountain --out out
continuity-forge shots tests/golden/fixtures/continuity.fountain --out out
continuity-forge pipeline tests/golden/fixtures/continuity.fountain --out out
continuity-forge proof tests/golden/fixtures/continuity.fountain --out out
continuity-forge-mcp
```

## Controlled proof

`continuity-forge proof` runs ingest → kernel pipeline → mock generate/validate/repair for every scene master shot and writes a versioned **proof receipt**.

The receipt explicitly claims `controlled_proof_not_production_ready`. It does **not** produce real video or claim feature-length readiness.

## Operator UI (Hallmark) · v1.3

A technical/austere **proof workbench** lives under `apps/web/` (Terminal theme · Workbench macrostructure). Primary action: run controlled proof and read the receipt.

```bash
# from repo root, with the package installed
make ui
# open http://127.0.0.1:8080/
```

| Endpoint | Role |
|----------|------|
| `POST /v1/proof` | Controlled proof (mock media) → `ProofReceipt` |
| `GET /v1/projects` | Tenant-scoped project list |
| `GET /v1/projects/{key}/status` | Canon status (scenes, shots, hashes) |
| `GET/POST/DELETE …/lease` | Write lease inspect / acquire / release |
| `GET …/approvals` | List approvals for a document |
| `POST /v1/approvals/request\|decide` | Request or grant/deny |
| `GET …/runs` | Pipeline runs for a document |
| `POST /v1/compile` | Dry compile (used by “Compile only”) |
| `POST /v1/tenants/bootstrap-dev` | Local dev API key |

Static UI is served at `/` when `apps/web` is present. Optional `Authorization: Bearer <api-key>` when `CF_AUTH_REQUIRED=1`.

Workbench: export receipt, canon status, **Control** panel (leases, approvals grant/deny, runs).

Design system tokens: `tokens.css` (root) and `apps/web/tokens.css`.

## Authority rule

```text
SOURCE SCRIPT -> DETERMINISTIC PARSER -> VALIDATED PRODUCTION IR
              -> CONTINUITY LEDGER -> SHOT CONTRACTS
              -> (mock) GENERATOR/VALIDATOR/REPAIR -> PROPOSED ARTIFACTS
```

Canonical state changes require schema validation, source provenance, deterministic diagnostics, authorization, and an expected-state hash where applicable.

## Campaigns

See `docs/campaigns/` for M0–M7 campaign specifications.

## Production stack (1.1)

| Capability | How |
|------------|-----|
| **Runtime wiring** | `continuity_forge_runtime.get_runtime()` selects memory / filesystem / Postgres + S3 from env |
| **OpenAI / Runway workers** | `CF_PROVIDER=openai\|runway` + API keys; injectable clients in tests |
| **HTTP gateway worker** | `CF_PROVIDER=http` + `CF_PROVIDER_HTTP_URL` |
| **Temporal deployment** | `deploy/docker-compose.yml` (Temporal + worker + UI) |
| **PostgreSQL stores** | `CF_DATABASE_URL` |
| **Filesystem durability** | `CF_STORE_ROOT=/path` |
| **S3 / MinIO artifacts** | `CF_S3_*` (candidates stored on generate) |
| **Multi-tenant auth** | `Authorization: Bearer <api-key>`; keys scoped as `{tenant}::{document}` |

```bash
# offline
continuity-forge worker-check
continuity-forge-worker --check

# full local stack + smoke
docker compose -f deploy/docker-compose.yml up --build
bash deploy/smoke.sh
```

See [`deploy/README.md`](deploy/README.md).

Extras: `pip install -e '.[production]'` (temporal, postgres, s3, openai, httpx).

## License / status

Private research codebase. Controlled proof uses mock media; production providers are optional and env-gated.
