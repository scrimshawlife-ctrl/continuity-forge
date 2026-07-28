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

## Authority rule

```text
SOURCE SCRIPT -> DETERMINISTIC PARSER -> VALIDATED PRODUCTION IR
              -> CONTINUITY LEDGER -> SHOT CONTRACTS
              -> (mock) GENERATOR/VALIDATOR/REPAIR -> PROPOSED ARTIFACTS
```

Canonical state changes require schema validation, source provenance, deterministic diagnostics, authorization, and an expected-state hash where applicable.

## Campaigns

See `docs/campaigns/` for M0–M7 campaign specifications.

## Post-1.0 foundations (rc2)

- **Filesystem stores:** `FileRunStore`, `FileProjectStore` for durable local state
- **In-process worker:** `continuity-forge worker-dry-run <script>` (Temporal-shaped, no cluster)
- **Provider registry:** `CF_PROVIDER=mock` (default); `openai`/`runway` fail closed until keys exist
- Optional: `pip install 'continuity-forge[temporal]'` for `temporalio` (cluster still required to host)

### Still later

- Real provider SDK implementations
- Hosted Temporal cluster worker process
- PostgreSQL + object storage
- Multi-tenant authN/Z

## License / status

Private research codebase. Mock media path is for continuity control proofs only.
