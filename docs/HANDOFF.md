# Continuity Forge — Handoff guide (working product path)

**Goal:** A user pastes or imports a screenplay and receives a **shot-by-shot breakdown with continuity**, as **machine-readable JSON** (connectors/API) and optional **Markdown** export.

**Release:** **v1.5.3** (`git checkout v1.5.3`) · Claim: `shot_breakdown_with_continuity_not_production_film`  
Built on frozen **v1.4.0** kernel. This is **not** production film and does **not** generate ACCEPTED media.

---

## Product path (what “working” means)

```text
Screenplay (Fountain or FDX text)
        │
        ▼
  compile → continuity ledger → shot contracts
        │
        ▼
  BreakdownPackage (cf.breakdown.v1)
        │
        ├── JSON  → file / POST response / MCP tool  (connectors)
        └── Markdown → human review / docs export
```

Each **shot** row includes slugline, label, required entities, constraints, state hashes, and continuity context (characters, props, setup/payoff names).

---

## 1. Operator UI (paste)

```bash
make ui
# open http://127.0.0.1:8080/
```

1. Paste Fountain/FDX into the script field, use **Import file** (or drag a file onto the textarea), or **Reset sample**.  
2. Click **Build breakdown**.  
3. Review shot table + scene nav.  
4. **Download breakdown JSON** (connector-ready) or **Download breakdown MD**.

Optional: **Run proof** for mock media repair loop (separate claim; not required for breakdown handoff).

Keyboard: **⌘/Ctrl+Enter** builds breakdown. Sticky mobile CTA is **Build breakdown**.

---

## 2. CLI (import file)

```bash
pip install -e '.[dev]'
continuity-forge breakdown path/to/script.fountain --out out
# → out/script.breakdown.json
# → out/script.breakdown.md
```

---

## 3. REST API (connector)

```bash
curl -s http://127.0.0.1:8080/v1/breakdown \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "My Script",
    "document_key": "my-script",
    "format": "fountain",
    "text": "INT. ROOM - DAY\n\nMara enters.\n"
  }' | jq .
```

Markdown variant:

```bash
curl -s http://127.0.0.1:8080/v1/breakdown/markdown \
  -H 'Content-Type: application/json' \
  -d @payload.json | jq -r .markdown
```

OpenAPI: `http://127.0.0.1:8080/docs`

Live connector smoke (API must be up via `make ui`):

```bash
make connector-smoke
# or: bash scripts/connector_smoke.sh [path/to/script.fountain]
```

Related read endpoints (same source body shape as compile):

| Method | Path | Output |
|--------|------|--------|
| POST | `/v1/breakdown` | Full `BreakdownPackage` JSON |
| POST | `/v1/breakdown/markdown` | `{ markdown, package_hash, counts… }` |
| POST | `/v1/compile` | Production IR only |
| POST | `/v1/continuity-ledger` | Continuity ledger only |
| POST | `/v1/shot-contracts` | Shot contract bundle only |

Auth: off by default (`CF_AUTH_REQUIRED` unset). When auth is on, send `Authorization: Bearer <tenant_key>`.

---

## 4. MCP / Hermes (agent connector)

Tools:

- `build_breakdown` — JSON package  
- `build_breakdown_markdown` — Markdown export  

Skill: `skills/hermes-continuity-forge/` · inventory: `references/mcp-tools.md`.

---

## 5. Package shape (`cf.breakdown.v1`)

| Field | Purpose |
|-------|---------|
| `schema_version` | `cf.breakdown.v1` |
| `claim` | Non-production claim string |
| `package_hash` | Content hash of package (excl. self) |
| `source_hash` / IR / ledger / shots hashes | Provenance |
| `scenes[]` | Scene ordinal, slugline, cast/props |
| `entities[]` | Continuity entities (character/location/prop/…) |
| `setup_payoff_links[]` | Setup → payoff scene links |
| `shots[]` | Shot-by-shot rows (constraints + continuity context) |

---

## 6. Automated test harness

```bash
make handoff
# or
python scripts/handoff_harness.py
```

Checks:

1. Kernel `build_breakdown_from_text` on golden fixtures  
2. Deterministic `package_hash`  
3. REST `/v1/breakdown` + `/v1/breakdown/markdown`  
4. CLI `continuity-forge breakdown` writes JSON + MD  

Unit/contract tests also cover this path under `make validate`.

---

## 7. Handoff checklist for a receiving team

- [ ] `git checkout v1.5.3` · `pip install -e '.[dev]'` · `make validate` (includes handoff)  
- [ ] `make ui` · Import file or sample · Build breakdown · download JSON  
- [ ] Curl `/v1/breakdown` or `make connector-smoke` (with API up)  
- [ ] Confirm `/health` reports `"version": "1.5.3"`  
- [ ] Read claim: not production film; PROPOSED media is a separate path  

---

## What this path does **not** do

- Live video generation or ACCEPTED media  
- Production Temporal fleet  
- Billing / OAuth multi-tenant product  

Those are post-baseline (1.5+) tracks. The breakdown package is the stable connector contract for **structure + continuity**.
