# Production-shaped local stack

```bash
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

Dev API key (when `CF_BOOTSTRAP_DEV_TENANT=1`):

```bash
curl -s http://localhost:8080/v1/tenants/bootstrap-dev
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
