# Bare-metal Linux install (no Docker)

Run Continuity Forge as a **native Linux service**: Python venv + systemd + optional
local Postgres/MinIO/Temporal. Docker Compose remains available for a production-*shaped*
all-in-one stack (`deploy/README.md`) but is **not required**.

| Artifact | Path |
|----------|------|
| Env template | [`deploy/linux/continuity-forge.env.example`](../deploy/linux/continuity-forge.env.example) |
| API unit | [`deploy/linux/continuity-forge-api.service`](../deploy/linux/continuity-forge-api.service) |
| Worker unit | [`deploy/linux/continuity-forge-worker.service`](../deploy/linux/continuity-forge-worker.service) |
| Install helper | [`deploy/linux/install.sh`](../deploy/linux/install.sh) |

---

## 1. System packages (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install -y \
  python3.12 python3.12-venv python3-pip \
  git build-essential curl
```

**Optional durability (pick what you need):**

```bash
# Postgres (canon / runs)
sudo apt install -y postgresql postgresql-contrib

# MinIO — not always in apt; use upstream binary or keep artifacts on disk via CF_STORE_ROOT
# Temporal — install upstream package or run only the in-process harness (no worker unit)
```

---

## 2. Layout (recommended)

```text
/opt/continuity-forge          # git clone + .venv
/var/lib/continuity-forge      # CF_STORE_ROOT (projects, runs, auth.json, artifacts)
/etc/continuity-forge/         # continuity-forge.env
```

```bash
sudo git clone https://github.com/scrimshawlife-ctrl/continuity-forge.git /opt/continuity-forge
cd /opt/continuity-forge
```

---

## 3. One-shot install helper

```bash
sudo bash deploy/linux/install.sh
```

This creates user `continuity-forge`, data dirs, env file, venv, installs `.[dev]`,
and installs systemd units (**does not** start the service until you enable it).

Manual equivalent:

```bash
sudo useradd --system --home-dir /var/lib/continuity-forge --shell /usr/sbin/nologin continuity-forge || true
sudo mkdir -p /var/lib/continuity-forge /etc/continuity-forge
sudo chown continuity-forge:continuity-forge /var/lib/continuity-forge
sudo cp deploy/linux/continuity-forge.env.example /etc/continuity-forge/continuity-forge.env
sudo chown root:continuity-forge /etc/continuity-forge/continuity-forge.env
sudo chmod 0640 /etc/continuity-forge/continuity-forge.env

sudo -u continuity-forge python3.12 -m venv /opt/continuity-forge/.venv
sudo -u continuity-forge /opt/continuity-forge/.venv/bin/pip install -U pip
sudo -u continuity-forge bash -c 'cd /opt/continuity-forge && .venv/bin/pip install -e ".[dev]"'
# optional Postgres/S3/Temporal clients:
# sudo -u continuity-forge bash -c 'cd /opt/continuity-forge && .venv/bin/pip install -e ".[production]"'

sudo cp deploy/linux/continuity-forge-api.service /etc/systemd/system/
sudo cp deploy/linux/continuity-forge-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
```

---

## 4. Configure environment

```bash
sudo nano /etc/continuity-forge/continuity-forge.env
```

### Minimal single-node (filesystem durability, mock providers)

```bash
CF_ENV=production
CF_HOST=127.0.0.1
CF_PORT=8080
CF_AUTH_REQUIRED=1
CF_BOOTSTRAP_DEV_TENANT=0
CF_STORE_ROOT=/var/lib/continuity-forge
CF_PROVIDER=mock
```

Runtime selection (`continuity_forge_runtime.get_runtime()`):

1. `CF_DATABASE_URL` → Postgres stores  
2. else `CF_STORE_ROOT` → filesystem stores + local artifact dir  
3. else in-memory (not for multi-process servers)

### Postgres backend

```bash
sudo -u postgres createuser continuity
sudo -u postgres createdb -O continuity continuity_forge
sudo -u postgres psql -c "ALTER USER continuity PASSWORD 'CHANGE_ME';"

# in env:
# CF_DATABASE_URL=postgresql://continuity:CHANGE_ME@127.0.0.1:5432/continuity_forge
# Keep or drop CF_STORE_ROOT; DB wins for project/run stores. Artifacts still need CF_STORE_ROOT or S3.
```

### Auth keys (production)

Bootstrap-dev is **blocked** when `CF_ENV`/`ENVIRONMENT` is `production`/`prod`.

Provision keys via your own process using `continuity_forge_auth` against
`${CF_STORE_ROOT}/auth.json`, or temporarily:

```bash
# ONE-TIME local admin only — never leave on a public host
# CF_ENV=development
# CF_BOOTSTRAP_DEV_TENANT=1
# restart, curl bootstrap, then set CF_ENV=production and CF_BOOTSTRAP_DEV_TENANT=0
```

---

## 5. Start the API (systemd)

```bash
sudo systemctl enable --now continuity-forge-api
sudo systemctl status continuity-forge-api --no-pager
journalctl -u continuity-forge-api -f
```

Health and UI:

```bash
curl -s http://127.0.0.1:8080/health
# open browser: http://127.0.0.1:8080/
```

Reverse-proxy (optional): put nginx/Caddy in front, TLS terminate, proxy to
`127.0.0.1:8080`. Keep `CF_HOST=127.0.0.1` so the app is not world-bound.

---

## 6. Optional Temporal worker

Requires Temporal frontend listening (e.g. `127.0.0.1:7233`) and:

```bash
sudo -u continuity-forge bash -c 'cd /opt/continuity-forge && .venv/bin/pip install -e ".[production]"'
# set CF_TEMPORAL_HOST in env file
sudo systemctl enable --now continuity-forge-worker
```

In-process pipeline still works **without** Temporal via API/CLI.

---

## 7. Smoke without Docker

```bash
# as continuity-forge or with env loaded
set -a; source /etc/continuity-forge/continuity-forge.env; set +a
curl -sf "http://${CF_HOST:-127.0.0.1}:${CF_PORT:-8080}/health"

# controlled proof via CLI
sudo -u continuity-forge /opt/continuity-forge/.venv/bin/continuity-forge proof \
  /opt/continuity-forge/tests/golden/fixtures/continuity.fountain \
  --out /tmp/cf-proof-out
```

API proof (with auth key if required):

```bash
curl -sf -X POST "http://127.0.0.1:8080/v1/proof" \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke","document_key":"linux-smoke","text":"INT. ROOM - DAY\n\nMara.\n","seed":"linux"}'
```

Full compose smoke script still assumes Docker ports; for bare metal use the curls above.

---

## 8. Updates

```bash
cd /opt/continuity-forge
sudo -u continuity-forge git pull --ff-only
sudo -u continuity-forge .venv/bin/pip install -e '.[dev]'   # or .[production]
sudo -u continuity-forge .venv/bin/python scripts/validate_m0.py
sudo systemctl restart continuity-forge-api
# sudo systemctl restart continuity-forge-worker
```

---

## 9. Security checklist

| Item | Guidance |
|------|----------|
| Bind address | Prefer `CF_HOST=127.0.0.1` + reverse proxy TLS |
| Bootstrap | `CF_BOOTSTRAP_DEV_TENANT=0` and `CF_ENV=production` |
| Env file | `0640` root:`continuity-forge` |
| Data dir | Owned by service user; not world-readable |
| Secrets | Never commit real `continuity-forge.env` |
| Providers | Keep `CF_PROVIDER=mock` until keys and budgets are real |

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `unit not found` | `daemon-reload` after copying unit files |
| Permission denied on store | `chown -R continuity-forge:continuity-forge /var/lib/continuity-forge` |
| Import / module not found | Activate venv path in `ExecStart`; reinstall `-e .` |
| Auth 401 | Issue API key; send `Authorization: Bearer …` |
| Bootstrap 403 | Expected when `CF_ENV=production` |
| Postgres connection refused | Start `postgresql`, fix `CF_DATABASE_URL` |
| UI 404 static | Confirm `apps/web` present in clone (not a bare wheel install without static) |

**Note:** Editable install from a full git tree is required for the Hallmark UI
static mount (`apps/web`). A wheel-only install may expose API without the UI
unless you also deploy `apps/web` and set a future `CF_WEB_ROOT` (not required
when running from the recommended `/opt/continuity-forge` clone).

---

## Related

- [SETUP.md](SETUP.md) — general install (dev laptop, Docker, MCP)
- [deploy/README.md](../deploy/README.md) — Docker Compose stack
- [AGENTS.md](../AGENTS.md) — mutation / canon authority
