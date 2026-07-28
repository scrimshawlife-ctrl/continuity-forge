# Continuity Forge

[![CI](https://github.com/scrimshawlife-ctrl/continuity-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/scrimshawlife-ctrl/continuity-forge/actions/workflows/ci.yml)

**A deterministic cinematic-production kernel and model-agnostic harness for drift-resistant AI film generation.**

Continuity Forge converts a screenplay into a provenance-preserving Production IR, continuity ledger, scene graph, and model-neutral shot contracts. Generative models may propose or render artifacts; they do not own canonical narrative state.

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.

**Version 1.3.0.** Default PR gate: `scripts/validate_m0.py` via `.github/workflows/ci.yml` (`make validate`). Phase 2: packaging (`.github/workflows/ci-packaging.yml`) and Postgres/MinIO integration smoke (`.github/workflows/ci-integration.yml`) — see `docs/SETUP.md` §3.

| Doc | Contents |
|-----|----------|
| **[docs/SETUP.md](docs/SETUP.md)** | Full install, env, UI, MCP, Docker |
| **[docs/hermes/README.md](docs/hermes/README.md)** | Hermes skill + MCP integration |
| **[skills/hermes-continuity-forge/](skills/hermes-continuity-forge/)** | Ready-to-install Hermes operator skill |
| **[AGENTS.md](AGENTS.md)** | Authority + mutation contract for agents |
| **[docs/architecture/](docs/architecture/)** | Harness architecture (authoritative boundaries) |

---

## Architecture

1. **Deterministic kernel** — screenplay, Production IR, continuity state, invariants, approvals, artifact lineage.
2. **Durable production harness** — pipeline commands, idempotency, checkpoints, Temporal adapter contracts.
3. **Operator surface** — project store, write leases, MCP/REST, Hallmark UI.
4. **Provider gateway + repair loop** — PROPOSED candidates; mock by default; real providers env-gated.
5. **Controlled proof** — end-to-end mock path + versioned receipt.

Canonical architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)

**Hermes** is the preferred operator agent (MCP + skill). **OpenClaw** may use the same contracts. Neither owns canon.

---

## Milestone status

Status labels (do not conflate):

| Label | Meaning |
|-------|---------|
| **Implemented** | Code and package/unit coverage exist on `main` (default CI: `make validate`). |
| **Integration-tested** | Exercised under the Phase 2 integration or packaging gates (or equivalent live service smoke). |
| **Production-validated** | Proven in a real production deployment with operator authority — **none of the milestones below claim this yet**. |

```text
M0 COMPILER SPINE .................... Implemented
M1 CONTINUITY LEDGER ................. Implemented
M2 SHOT CONTRACT COMPILER ............ Implemented
M3 DURABLE HARNESS / TEMPORAL ........ Implemented (in-process + adapter contracts; Temporal fleet not production-validated)
M4 MCP OPERATOR SURFACE .............. Implemented
M5 PROVIDER GATEWAY + WORKERS ........ Implemented (mock default; real providers env-gated, not production-validated)
M6 GENERATOR-EVALUATOR REPAIR LOOP ... Implemented (mock default)
M7 CONTROLLED 30-60s PROOF ........... Implemented (mock media; claim controlled_proof_not_production_ready)
POST-1.0 runtime / auth / deploy ..... Implemented; Postgres/MinIO path Integration-tested (CI smoke skeleton)
OPERATOR UI (Hallmark) ............... Implemented (v1.3.0 UI surface)
HERMES SKILL ......................... Implemented (skills/hermes-continuity-forge)
```

Nothing in this table is **Production-validated**. Controlled proof and mock paths are not production film.

---

## Quick start (install & setup)

**Requires:** Python 3.12+, pip, git.

```bash
git clone https://github.com/scrimshawlife-ctrl/continuity-forge.git
cd continuity-forge
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e '.[dev]'            # or: make install
make validate                      # ruff + mypy + pytest (CI parity)
make proof                         # golden controlled proof → out/
```

Production extras (Temporal, Postgres, S3, OpenAI, HTTP worker):

```bash
pip install -e '.[production]'
```

Full guide (env vars, Docker, troubleshooting): **[docs/SETUP.md](docs/SETUP.md)**.

### CLI

| Command | Role |
|---------|------|
| `continuity-forge` | compile / ledger / shots / pipeline / proof |
| `continuity-forge-mcp` | Stdio MCP for Hermes / OpenClaw |
| `continuity-forge-worker` | Temporal worker |

```bash
continuity-forge compile tests/golden/fixtures/minimal.fountain --out out
continuity-forge ledger tests/golden/fixtures/continuity.fountain --out out
continuity-forge shots tests/golden/fixtures/continuity.fountain --out out
continuity-forge pipeline tests/golden/fixtures/continuity.fountain --out out
continuity-forge proof tests/golden/fixtures/continuity.fountain --out out
```

### Operator UI + API

```bash
make ui
# → http://127.0.0.1:8080/   (proof workbench)
# → http://127.0.0.1:8080/docs  (OpenAPI)
# → http://127.0.0.1:8080/health
```

Default path in the UI: **script → Run proof → receipt**. Advanced (auth, leases, projects) is folded away.

Primary REST: `POST /v1/proof` → `ProofReceipt` with claim `controlled_proof_not_production_ready`.

### Hermes (agentic operator)

1. Install package (`pip install -e '.[dev]'`).
2. Copy skill: `cp -R skills/hermes-continuity-forge ~/.hermes/skills/` (or your Hermes skills path).
3. Wire MCP stdio to `.venv/bin/continuity-forge-mcp` — see [`docs/hermes/mcp.example.json`](docs/hermes/mcp.example.json).
4. Read [`docs/hermes/README.md`](docs/hermes/README.md).

To regenerate or extend the skill after tool changes, use  
[`docs/hermes/BUILD_SKILL_PROMPT.md`](docs/hermes/BUILD_SKILL_PROMPT.md).

### Docker (production-shaped local stack)

```bash
docker compose -f deploy/docker-compose.yml up --build
bash deploy/smoke.sh
```

Details: [`deploy/README.md`](deploy/README.md).

---

## Controlled proof

`continuity-forge proof` (and `POST /v1/proof`) runs ingest → kernel pipeline → mock generate/validate/repair and writes a versioned **proof receipt**.

The receipt claims **`controlled_proof_not_production_ready`**. It does **not** produce real video or claim feature-length readiness.

---

## Authority rule

```text
SOURCE SCRIPT -> DETERMINISTIC PARSER -> VALIDATED PRODUCTION IR
              -> CONTINUITY LEDGER -> SHOT CONTRACTS
              -> (mock/real) GENERATOR/VALIDATOR/REPAIR -> PROPOSED ARTIFACTS
```

Canonical mutations require schema validation, provenance, deterministic diagnostics, authorization, and an expected-state hash when continuing prior state. See [`AGENTS.md`](AGENTS.md).

---

## Production stack (1.3)

| Capability | How |
|------------|-----|
| **Runtime wiring** | `get_runtime()` → memory / filesystem / Postgres + S3 from env |
| **OpenAI / Runway** | `CF_PROVIDER=openai\|runway` + API keys |
| **HTTP worker** | `CF_PROVIDER=http` + `CF_PROVIDER_HTTP_URL` |
| **Temporal** | `deploy/docker-compose.yml` + `continuity-forge-worker` |
| **PostgreSQL** | `CF_DATABASE_URL` |
| **Filesystem** | `CF_STORE_ROOT` |
| **S3 / MinIO** | `CF_S3_*` |
| **Multi-tenant auth** | `Authorization: Bearer <key>`; keys `{tenant}::{document}` |

---

## Campaigns & ADRs

- Campaigns: [`docs/campaigns/`](docs/campaigns/)
- ADR-0001 harness: [`docs/adr/ADR-0001-production-harness.md`](docs/adr/ADR-0001-production-harness.md)
- Supported Fountain grammar (M0): [`docs/compiler/M0_SUPPORTED_GRAMMAR.md`](docs/compiler/M0_SUPPORTED_GRAMMAR.md)

---

## License / status

**Public research repository** ([github.com/scrimshawlife-ctrl/continuity-forge](https://github.com/scrimshawlife-ctrl/continuity-forge)). Source is published for research and collaboration; this is **not** a production-supported product release and does not imply production readiness.

Package version: **1.3.0** (kept in sync with [`pyproject.toml`](pyproject.toml) `[project].version` — no bump in this docs pass).

Controlled proof uses mock media; production providers and durability backends are optional and env-gated. See milestone labels above for Implemented vs Integration-tested vs Production-validated.
