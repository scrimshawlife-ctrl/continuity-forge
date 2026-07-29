# Continuity Forge

[![CI](https://github.com/scrimshawlife-ctrl/continuity-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/scrimshawlife-ctrl/continuity-forge/actions/workflows/ci.yml)

## What it does

Turn a screenplay into **continuity-aware scenes and shot packages**.

Import a script for a film, episode, commercial, music video, or short-form piece. Continuity Forge deterministically breaks it into scenes and shots, extracts continuity state, helps you review conflicts, and prepares **provider-neutral** generation packages — so visual and narrative continuity can hold across separate generative-model calls.

## Who it is for

Filmmakers, writers, producers, continuity reviewers, and pipeline integrators who need structured scene/shot continuity — not a generic chat window that “remembers” the script.

## How it works (product path)

```text
Create Project → Import Script → Analyze Script → Review Scenes & Continuity
  → Resolve Conflicts → Prepare Scene for Generation → Export or Generate → Review
```

Generative models may propose prompts and media. They do **not** silently own canonical narrative state. You review and approve.

## Quick start

```bash
git clone https://github.com/scrimshawlife-ctrl/continuity-forge.git
cd continuity-forge
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
make validate
make ui   # http://127.0.0.1:8080/ — New Project → Analyze Script
```

## Product workflow

See **[docs/PRODUCT_WORKFLOW.md](docs/PRODUCT_WORKFLOW.md)** and **[docs/HANDOFF.md](docs/HANDOFF.md)**.

Primary UI navigation: **Projects · Scenes · Continuity · Generate · Review · Export**.  
Engineering tools (hashes, mock pipeline test, raw JSON) live under **Settings → Developer**.

## Current capabilities

| Capability | Status |
|------------|--------|
| Script import (Fountain / FDX / txt) | Implemented |
| Analyze Script → scenes, entities, shots, conflicts | Implemented |
| Continuity review + provenance labels | Implemented |
| Provider-neutral scene packages + export-only path | Implemented |
| Deterministic breakdown JSON (`cf.breakdown.v1`) | Implemented |
| Mock generation / controlled proof | Implemented (Developer; not production film) |
| Live production fleet / ACCEPTED media | **Not production-validated** |

**Version 1.5.3** handoff pin remains available (`v1.5.3`). Product workflow UI continues on `main`. Baseline freeze: **`v1.4.0`**. Gate: `make validate` (includes handoff).

| Doc | Contents |
|-----|----------|
| **[docs/PRODUCT_WORKFLOW.md](docs/PRODUCT_WORKFLOW.md)** | Creative user journey + IA |
| **[docs/HANDOFF.md](docs/HANDOFF.md)** | Product path first, then CLI/API/MCP |
| **[docs/campaigns/CONTINUITY_FORGE_PRODUCT_WORKFLOW_UI_001.md](docs/campaigns/CONTINUITY_FORGE_PRODUCT_WORKFLOW_UI_001.md)** | UI simplification campaign |
| **[docs/releases/1.5.3.md](docs/releases/1.5.3.md)** | Handoff pin notes |
| **[docs/releases/1.4.0.md](docs/releases/1.4.0.md)** | Baseline freeze |
| **[docs/SETUP.md](docs/SETUP.md)** | Full install, env, Docker |
| **[docs/hermes/README.md](docs/hermes/README.md)** | Hermes skill + MCP |
| **[AGENTS.md](AGENTS.md)** | Authority + mutation contract |
| **[docs/architecture/](docs/architecture/)** | Kernel + operator UI boundaries |

---

## Architecture

1. **Deterministic kernel** — screenplay, Production IR, continuity state, invariants, approvals, artifact lineage.
2. **Durable production harness** — pipeline commands, idempotency, checkpoints, Temporal adapter contracts.
3. **Operator surface** — creative UI, project store, MCP/REST; Developer progressive disclosure.
4. **Provider gateway + repair loop** — proposed candidates; mock by default; real providers env-gated.
5. **Controlled proof** — end-to-end mock path (Developer tools).

Canonical architecture: [`docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md`](docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md) · UI: [`docs/architecture/OPERATOR_UI_ARCHITECTURE.md`](docs/architecture/OPERATOR_UI_ARCHITECTURE.md)

**Hermes** is the preferred operator agent (MCP + skill). **OpenClaw** may use the same contracts. Neither owns canon.

> Models generate pixels and proposals. Continuity Forge governs identity, memory, causality, approvals, and production truth.

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
OPERATOR UI (creative workspace) ..... Implemented (Projects/Scenes/Continuity/Generate/Review/Export)
HERMES SKILL ......................... Implemented (skills/hermes-continuity-forge)
LONG-FORM UX (Phase 4 audit) ......... Implemented (nav, invalidation, incremental, cost, events)
HANDOFF BREAKDOWN .................... Implemented (cf.breakdown.v1 JSON/MD + make handoff)
PRODUCT WORKFLOW UI .................. Implemented (Analyze Script path; Developer progressive disclosure)
```

Nothing in this table is **Production-validated**. Controlled proof and mock paths are not production film.

**Product UI:** New Project → Analyze Script → review scenes/continuity → export packages. See [`docs/PRODUCT_WORKFLOW.md`](docs/PRODUCT_WORKFLOW.md).

**Handoff (v1.5+):** paste/import → analyze → connector JSON. See [`docs/HANDOFF.md`](docs/HANDOFF.md).

**Pin a known-good tree:**

```bash
git checkout v1.5.3   # recommended handoff pin — see docs/releases/1.5.3.md
git checkout v1.4.0   # baseline freeze only — see docs/releases/1.4.0.md
```

Forward work continues on `main` (1.6+). `1.5.x` = handoff / UI fixes; `1.4.x` = freeze-story patches only.

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
make handoff                       # automated paste→breakdown→export/API checks
make breakdown                     # sample shot breakdown + continuity → out/
make proof                         # golden controlled proof → out/
```

**Handoff (shot breakdown + continuity):** paste a script in the UI (**Analyze Script**), or:

```bash
continuity-forge breakdown tests/golden/fixtures/continuity.fountain --out out
# → out/continuity.breakdown.json  (machine-readable)
# → out/continuity.breakdown.md    (text export)
# REST: POST /v1/breakdown  ·  MCP: build_breakdown
```

See **[docs/HANDOFF.md](docs/HANDOFF.md)**.

Production extras (Temporal, Postgres, S3, OpenAI, HTTP worker):

```bash
pip install -e '.[production]'
```

Full guide (env vars, Docker, troubleshooting): **[docs/SETUP.md](docs/SETUP.md)**.

**Bare-metal Linux (no Docker):** systemd units + env template — **[docs/LINUX.md](docs/LINUX.md)**  
(`deploy/linux/install.sh`, `continuity-forge-api.service`).

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

Package version: **1.5.3** (kept in sync with [`pyproject.toml`](pyproject.toml) `[project].version`).

Controlled proof uses mock media; production providers and durability backends are optional and env-gated. See milestone labels above for Implemented vs Integration-tested vs Production-validated.

## Narrative Engineering Companion Skill

In addition to the operator skill (`hermes-continuity-forge`), this repo ships **`skills/scriptwriting/`** — a production-grade narrative engineering system (premise → characters → structure → scene contracts → anti-slop → production handoff).

Use `scriptwriting` for creative development and structural work. Handoff approved material to Continuity Forge (via CLI or MCP) for canonical ledger, IR, and shot contracts.

See `skills/scriptwriting/SKILL.md` and `skills/scriptwriting/references/continuity-forge-integration.md`.

Install both:
```bash
cp -R skills/scriptwriting ~/.hermes/skills/
cp -R skills/hermes-continuity-forge ~/.hermes/skills/
```

## Symbolic Cinematic Layer: kubrick Skill

This repo ships `skills/kubrick/` — the primary symbolic cinematic narrative engineering system (replacement for the earlier scriptwriting skill).

It includes a full **provenance-linked Symbolic Narrative Pattern System**:

- `SymbolicNarrativePattern` core schema with observed_structure, cinematic_affordances, mutation_rules, and source provenance.
- Narrative Affordance Registry (BIND, DIVIDE, INITIATE, CONCEAL, REVEAL, INVERT, REPEAT, CONTAMINATE, MIRROR, SACRIFICE, CROSS, ENCLOSE, DESCEND, RETURN, HAUNT, ERASE, RESTORE, and others).
- Transformation Grammar Registry (alchemical and process-based operations mapped to narrative, character, blocking, shot, editing, and sound).
- Dedicated Cinematic Symbolism Corpus (shot scale, graphic matches, negative space, acousmatic sound, broken symmetry, motif transfer — no fixed meanings).
- 10 bounded corpus domains with source hierarchy (PRIMARY / SCHOLARLY / etc.) and explicit cross-tradition relationship types.
- Strict retrieval rules, quality gates, and validation tests that enforce historically grounded structures translated into subtle enactment without explanation or collage.

Use kubrick for premise-to-production work requiring precise symbolic architecture that survives revision and handoff. It produces `symbolic_architecture` + `cinematic_encoding` ready for Continuity Forge.

Handoff approved material to Continuity Forge (via CLI or MCP) for canonical ledger, IR, and shot contracts.

See:
- `skills/kubrick/SKILL.md`
- `skills/kubrick/references/symbolic-dramaturgy.md`
- `skills/kubrick/references/symbolic-narrative-patterns.yaml`
- `skills/kubrick/references/narrative-affordance-registry.md`
- `skills/kubrick/references/transformation-grammar-registry.md`
- `skills/kubrick/references/cinematic-symbolism-corpus.md`
- `skills/kubrick/references/corpus-usage.md`

Install:
```bash
cp -R skills/kubrick ~/.hermes/skills/
cp -R skills/hermes-continuity-forge ~/.hermes/skills/
```
