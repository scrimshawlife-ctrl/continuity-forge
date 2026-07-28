# Continuity Forge — Install & Setup

Complete install paths for kernel, operator UI, MCP (Hermes), production-shaped Docker,
and **bare-metal Linux** (systemd).

**Current release:** **[v1.5.0](releases/1.5.0.md)** — handoff (shot breakdown + continuity export).  
**Baseline freeze:** **[v1.4.0](releases/1.4.0.md)** — pre-handoff kernel.  
Pin handoff: `git checkout v1.5.0`. Not production film.

**Requirements:** Python **3.12+**, `pip`, git. Docker optional (full stack).

| Guide | When |
|-------|------|
| This file | Dev laptop, general env, MCP, Docker smoke |
| **[LINUX.md](LINUX.md)** | Native Linux server: systemd units, env file, no Docker required |

---

## 1. Clone & virtualenv

```bash
git clone https://github.com/scrimshawlife-ctrl/continuity-forge.git
cd continuity-forge
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -U pip
```

---

## 2. Install packages

### Developer (kernel + tests + API + MCP)

```bash
pip install -e '.[dev]'
# or
make install
```

### Production extras (Temporal, Postgres, S3, OpenAI, HTTP worker)

```bash
pip install -e '.[production]'
```

Extras are optional; mock providers and in-memory stores work without them.

---

## 3. Validate (CI parity)

### Fast gate (default PR / merge check)

```bash
make validate
# same as: python scripts/validate_m0.py
# gates: ruff · ruff format · mypy · pytest
```

GitHub Actions workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
runs the same script. **This is the default PR check** — keep it green before merge.

### Packaging gate (Phase 2)

Separate workflow: [`.github/workflows/ci-packaging.yml`](../.github/workflows/ci-packaging.yml).

Proves the distributable is installable outside an editable checkout:

1. `python -m build` → wheel + sdist under `dist/`
2. Install the wheel into a **clean** virtualenv
3. `continuity-forge --help`
4. Import smoke for all shipped packages (`continuity_forge_*` kernel + API/MCP)

Local reproduction:

```bash
python -m pip install 'build>=1.2,<2'
python -m build
python -m venv .venv-package
source .venv-package/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/continuity_forge-*.whl
continuity-forge --help
python -c "import continuity_forge_compiler, continuity_forge_api, continuity_forge_mcp"
```

Packaging runs on `main` pushes, PRs, and `workflow_dispatch`. It is **not** a
replacement for the fast `validate_m0` gate; treat it as a packaging/installability
check (required for release paths; optional-to-require for everyday PR merge policy).

### Integration gate (Phase 2 skeleton) — Postgres + MinIO

Separate workflow: [`.github/workflows/ci-integration.yml`](../.github/workflows/ci-integration.yml).

Proves optional durability backends respond under CI:

| Piece | Detail |
|-------|--------|
| Services | `postgres:16`, `bitnami/minio` (S3-compatible) |
| Install | `pip install -e '.[dev,production]'` |
| Env | `CF_DATABASE_URL`, `CF_S3_ENDPOINT`, `CF_S3_BUCKET`, `CF_S3_ACCESS_KEY`, `CF_S3_SECRET_KEY` |
| Tests | `tests/integration/test_postgres_minio_smoke.py` |

Smoke coverage (minimal):

1. **Postgres** — `PostgresRunStore` put + rehydrate/get of a `WorkflowRun`
2. **MinIO** — `S3ArtifactStore` put/get of a mock `ArtifactCandidate`

**Local behavior:** the same file is **skip-friendly**. Without `CF_DATABASE_URL` /
`CF_S3_*`, without `psycopg`/`boto3`, or when services are down, tests call
`pytest.skip` (they do not fail). Safe under `make validate` / default pytest.

Local reproduction (Docker services from deploy compose, or any Postgres 16 + MinIO):

```bash
pip install -e '.[dev,production]'
export CF_DATABASE_URL=postgresql://continuity:continuity@localhost:5432/continuity_forge
export CF_S3_ENDPOINT=http://127.0.0.1:9000
export CF_S3_BUCKET=continuity-forge
export CF_S3_ACCESS_KEY=minioadmin
export CF_S3_SECRET_KEY=minioadmin
# optional: docker compose -f deploy/docker-compose.yml up -d postgres minio minio-init
make test-integration
# same as: python -m pytest tests/integration/test_postgres_minio_smoke.py -v
```

Integration runs on `main` pushes, PRs, and `workflow_dispatch`. It is a Phase 2
skeleton for production-shaped backends — not a substitute for the fast gate.

Quick proof on golden fixture:

```bash
make proof
# writes out/continuity.proof-receipt.json (claim: controlled_proof_not_production_ready)
```

---

## 4. CLI surface

After install, entry points:

| Command | Role |
|---------|------|
| `continuity-forge` | Compiler / ledger / shots / pipeline / proof CLI |
| `continuity-forge-mcp` | Stdio MCP server for Hermes / OpenClaw |
| `continuity-forge-worker` | Temporal worker (needs Temporal host) |

Examples:

```bash
# Primary handoff: shot-by-shot breakdown + continuity (JSON + Markdown)
continuity-forge breakdown tests/golden/fixtures/continuity.fountain --out out
continuity-forge compile tests/golden/fixtures/minimal.fountain --out out
# Optional edit-loop path: full validate + prior-ID reconcile + invalidation receipt
continuity-forge compile tests/golden/fixtures/minimal.fountain --out out \
  --prior-ir out/minimal.production-ir.json --incremental
continuity-forge ledger tests/golden/fixtures/continuity.fountain --out out
continuity-forge shots tests/golden/fixtures/continuity.fountain --out out
continuity-forge pipeline tests/golden/fixtures/continuity.fountain --out out
continuity-forge proof tests/golden/fixtures/continuity.fountain --out out
```

REST handoff: `POST /v1/breakdown` (JSON) · `POST /v1/breakdown/markdown`.  
Also: `POST /v1/compile`; optional `POST /v1/compile/incremental` (read-side, not a canon write).  
Handoff guide: [`docs/HANDOFF.md`](HANDOFF.md). Automated check: `make handoff`.

Workflow progress (long-form 4.6, poll-first):

```bash
# After POST /v1/pipeline/runs → use run_id
curl -s "http://127.0.0.1:8080/v1/pipeline/runs/{run_id}/events"
# Resume without replaying mutations:
curl -s "http://127.0.0.1:8080/v1/pipeline/runs/{run_id}/events?after=2"
curl -s "http://127.0.0.1:8080/v1/pipeline/runs/{run_id}/events?last_event_id=..."
```

Events are observability only (`workflow_events_observability_not_canon`).
**Workflow complete ≠ production ready.** SSE is not required for the first slice.


---

## 5. Operator UI + REST API

```bash
make ui
# uvicorn continuity_forge_api.main:app --reload --port 8080
```

Open **http://127.0.0.1:8080/**

| Path | Role |
|------|------|
| `/` | Hallmark proof workbench (script → Run proof → receipt) |
| `/health` | Liveness + backend + version |
| `/v1/*` | REST operator API |
| `/docs` | OpenAPI (FastAPI) |

### Auth (optional locally)

By default auth is **off** (`CF_AUTH_REQUIRED` unset → anonymous principal).

```bash
export CF_AUTH_REQUIRED=1
export CF_BOOTSTRAP_DEV_TENANT=1   # local/dev only — never in production
# then either:
curl -s -X POST http://127.0.0.1:8080/v1/tenants/bootstrap-dev
# or use UI Advanced → Get local dev key
```

`POST /v1/tenants/bootstrap-dev` returns **403** unless `CF_BOOTSTRAP_DEV_TENANT`
is truthy. It is **always disabled** when `CF_ENV` or `ENVIRONMENT` is
`production` / `prod`, even if the bootstrap flag is set.

Document keys are tenant-scoped as `{tenant}::{document}` (never use `/` in keys).
Tenant A cannot read or write Tenant B's document keys; foreign prefixes are
re-scoped under the caller's tenant.

### Useful env

| Variable | Purpose |
|----------|---------|
| `CF_AUTH_REQUIRED` | `1` to require Bearer API keys |
| `CF_BOOTSTRAP_DEV_TENANT` | Seed local `dev` tenant / enable bootstrap-dev route (**local only**) |
| `CF_ENV` / `ENVIRONMENT` | Set `production`/`prod` to force-disable bootstrap-dev |
| `CF_STORE_ROOT` | Filesystem durability root |
| `CF_DATABASE_URL` | Postgres stores |
| `CF_S3_*` / MinIO | Artifact candidates |
| `CF_PROVIDER` | `mock` (default) · `openai` · `runway` · `http` |
| `CF_PROVIDER_HTTP_URL` | When `CF_PROVIDER=http` |
| `CF_TEMPORAL_HOST` | Temporal frontend for worker |

See also [`deploy/README.md`](../deploy/README.md).

---

## 6. MCP for Hermes / OpenClaw

```bash
# from activated venv with package installed
continuity-forge-mcp
```

Hermes should launch this as a **stdio** MCP server. Example config fragment:

```json
{
  "mcpServers": {
    "continuity-forge": {
      "command": "/absolute/path/to/continuity-forge/.venv/bin/continuity-forge-mcp",
      "args": [],
      "env": {
        "CF_STORE_ROOT": "/absolute/path/to/cf-data"
      }
    }
  }
}
```

Use the **absolute path** to the venv binary so Hermes does not depend on shell `PATH`.

Full agent skill + workflows:

- Skill: [`skills/hermes-continuity-forge/SKILL.md`](../skills/hermes-continuity-forge/SKILL.md)
- Integration: [`docs/hermes/README.md`](hermes/README.md)
- Meta-prompt to regenerate/extend the skill: [`docs/hermes/BUILD_SKILL_PROMPT.md`](hermes/BUILD_SKILL_PROMPT.md)

---

## 7. Production-shaped Docker stack

```bash
docker compose -f deploy/docker-compose.yml up --build
bash deploy/smoke.sh
```

| Service | Port | Role |
|---------|------|------|
| api | 8080 | FastAPI + UI + auth |
| temporal | 7233 | Workflow engine |
| temporal-ui | 8088 | Temporal UI |
| postgres | 5432 | Durable stores |
| minio | 9000 / 9001 | S3 artifacts |
| worker | — | Temporal kernel worker |

Details: [`deploy/README.md`](../deploy/README.md).

---

## 8. Recommended first hour

1. `pip install -e '.[dev]'` → `make validate`
2. `make proof` → inspect `out/`
3. `make ui` → Run proof in browser
4. Install Hermes skill + wire MCP (`docs/hermes/`)
5. Optional: `docker compose -f deploy/docker-compose.yml up --build`

---

## 9. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `command not found: continuity-forge` | Activate venv; re-run `pip install -e '.[dev]'` |
| UI blank / API offline | Confirm `make ui` and open same host:port |
| Auth 401 | Bootstrap key; send `Authorization: Bearer <key>` |
| MCP tools empty in Hermes | Absolute path to `continuity-forge-mcp`; check Hermes MCP logs |
| mypy/ruff fail locally | Same as CI — fix before push |
| Postgres/S3 import errors | Install `.[production]` only when using those backends |

---

## 10. Authority (do not skip)

```text
SOURCE SCRIPT → DETERMINISTIC PARSER → VALIDATED PRODUCTION IR
              → CONTINUITY LEDGER → SHOT CONTRACTS
              → (mock/real) GENERATOR/VALIDATOR/REPAIR → PROPOSED ARTIFACTS
```

- Models never own canon.
- Mutations need actor · scope · idempotency · rationale · expected-state hash when continuing.
- Controlled proof claims **`controlled_proof_not_production_ready`**.
