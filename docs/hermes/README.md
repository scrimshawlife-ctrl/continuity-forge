# Hermes integration — Continuity Forge

Hermes is the **preferred operator agent**. It does **not** own canon, leases, or provider credentials. It drives Continuity Forge through:

1. **MCP** — `continuity-forge-mcp` (stdio tools + `cf://` resources)
2. **REST** — optional parallel surface (`POST /v1/proof`, projects, approvals)
3. **Skill** — operator playbooks and hard authority rules

OpenClaw may use the same MCP/REST contracts as an alternate client.

---

## Install skill

Copy (or symlink) the skill into Hermes’ skills directory:

```bash
# from continuity-forge repo root
mkdir -p ~/.hermes/skills   # adjust if your Hermes install uses another path
cp -R skills/hermes-continuity-forge ~/.hermes/skills/
# or project-local, if Hermes supports workspace skills:
# cp -R skills/hermes-continuity-forge /path/to/workspace/.hermes/skills/
```

Skill root:

```text
skills/hermes-continuity-forge/
  SKILL.md
  references/
    mcp-tools.md
    mutation-contract.md
    workflows.md
```

Trigger phrases (see skill frontmatter): continuity forge, controlled proof, shot contracts, write lease, MCP operator, ingest script, PROPOSED candidate.

---

## Wire MCP

1. Install the package so the entrypoint exists:

   ```bash
   source .venv/bin/activate
   pip install -e '.[dev]'
   which continuity-forge-mcp
   ```

2. Add a stdio MCP server to Hermes config (path must be absolute):

   See [`mcp.example.json`](mcp.example.json).

3. Restart Hermes / reload MCP. Confirm tools such as `compile_script`, `ingest_script`, `run_shot_repair_loop` appear.

### Env for durable local MCP

```bash
export CF_STORE_ROOT="$HOME/.local/share/continuity-forge"
# optional:
export CF_PROVIDER=mock
# export CF_DATABASE_URL=...
```

Pass the same env in the MCP server config so Hermes-spawned processes see them.

---

## Operator boundaries (non-negotiable)

| Hermes may | Hermes must not |
|------------|-----------------|
| Compile / ledger / shots (reads) | Treat chat memory as film canon |
| Hold write leases, ingest with mutation contract | Mutate without actor + scope + idempotency + rationale |
| Queue generation / repair loop | Claim production-ready film or real media when mock |
| Surface receipts and drift | Bypass approval thresholds for identity locks / canon changes |
| Call REST `/v1/proof` for controlled proof | Run unbounded “director” loops without shot contracts |

Full rules: skill `SKILL.md` + [`mutation-contract.md`](../../skills/hermes-continuity-forge/references/mutation-contract.md).

---

## Default agentic workflows

Documented in [`workflows.md`](../../skills/hermes-continuity-forge/references/workflows.md):

1. **Controlled proof** — golden or user fountain → receipt
2. **Ingest under lease** — acquire lease → ingest → status
3. **Shot repair** — queue generation / repair loop → PROPOSED only
4. **Drift audit** — ledger diagnostics (CL2*)
5. **Approval handoff** — request / decide only with lease + rationale

---

## Regenerating or extending the skill

Use the meta-prompt:

[`BUILD_SKILL_PROMPT.md`](BUILD_SKILL_PROMPT.md)

Feed it to Hermes (or another coding agent) when MCP tools or REST surface change.

---

## Related docs

- [Setup](../SETUP.md)
- [MCP server README](../../apps/mcp/src/continuity_forge_mcp/README.md)
- [Architecture](../architecture/PRODUCTION_HARNESS_ARCHITECTURE.md)
- [AGENTS.md](../../AGENTS.md)
