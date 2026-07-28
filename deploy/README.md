# Production-shaped local stack

Prerequisites and general install: **[docs/SETUP.md](../docs/SETUP.md)**.  
**Bare-metal Linux (systemd, no Docker):** **[docs/LINUX.md](../docs/LINUX.md)** · units under [`linux/`](linux/).

## CI gates (install vs runtime)

| Workflow | Role | Default PR merge? |
|----------|------|-------------------|
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Fast gate: `scripts/validate_m0.py` (ruff · format · mypy · pytest) | **Yes** — keep green |
| [`.github/workflows/ci-packaging.yml`](../.github/workflows/ci-packaging.yml) | Phase 2 packaging: `python -m build` → clean-venv wheel install → `continuity-forge --help` + import smoke | Separate check (installability) |

Local packaging smoke (parity with packaging CI) is documented in
[`docs/SETUP.md`](../docs/SETUP.md) §3. Docker/runtime smoke below is complementary
and exercises the compose stack, not the wheel build.

```bash
# from repo root; prefer production extras inside the image (Dockerfile installs .[production])
docker compose -f deploy/docker-compose.yml up --build
# after API is healthy:
bash deploy/smoke.sh
```

The API selects backends via env (`CF_DATABASE_URL`, `CF_S3_*`, `CF_PROVIDER`, `CF_AUTH_REQUIRED`) through `continuity_forge_runtime.get_runtime()`.

Services:

| Service | Port | Role |
|---------|------|------|
| api | 8080 | FastAPI + multi-tenant auth + operator UI (`/`) |
| worker | — | Temporal worker (`continuity-forge-worker`) |
| temporal | 7233 | Temporal frontend |
| temporal-ui | 8088 | Temporal UI |
| postgres | 5432 | Canon/run durability |
| minio | 9000 / 9001 | S3-compatible artifacts |

Operator workbench (Hallmark Terminal / Workbench): open `http://localhost:8080/` after the API is up. Primary action is `POST /v1/proof` (controlled mock proof + receipt).

### Dev bootstrap (local only — never production)

> **WARNING:** `CF_BOOTSTRAP_DEV_TENANT` and `POST /v1/tenants/bootstrap-dev` are
> **local/dev only**. Do **not** set this flag in real production configs. The
> route returns **403** unless `CF_BOOTSTRAP_DEV_TENANT` is truthy, and is always
> blocked when `CF_ENV` or `ENVIRONMENT` is `production` / `prod` (even if the
> flag is set). This compose stack is production-*shaped* for local exercise;
> it enables bootstrap intentionally for smoke tests — strip it before any
> shared/staging/production deploy.

Dev API key (when `CF_BOOTSTRAP_DEV_TENANT=1` and not in production env):

```bash
curl -s -X POST http://localhost:8080/v1/tenants/bootstrap-dev
# {"tenant_id":"dev","api_key":"dev-local-key"}

curl -s -H "Authorization: Bearer dev-local-key" http://localhost:8080/v1/whoami
```

Optional extras for bare-metal:

```bash
pip install -e '.[production]'
export CF_DATABASE_URL=postgresql://continuity:continuity@localhost:5432/continuity_forge
export CF_S3_ENDPOINT=http://localhost:9000
export CF_S3_BUCKET=continuity-forge
export CF_S3_ACCESS_KEY=minioadmin
export CF_S3_SECRET_KEY=minioadmin
export CF_AUTH_REQUIRED=1
export OPENAI_API_KEY=...
export RUNWAY_API_KEY=...
```

### CI integration smoke (Phase 2 skeleton)

GitHub Actions [`.github/workflows/ci-integration.yml`](../.github/workflows/ci-integration.yml)
spins up Postgres 16 + MinIO and runs
`tests/integration/test_postgres_minio_smoke.py` with the same `CF_DATABASE_URL` /
`CF_S3_*` shape as above. Locally those tests **skip** if services or
`.[production]` extras are missing (`make test-integration`). Details:
[`docs/SETUP.md`](../docs/SETUP.md) §3.
