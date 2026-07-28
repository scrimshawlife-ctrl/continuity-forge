# Prompt: build / refresh the Hermes Continuity Forge operator skill

Use this when the MCP tool list, REST surface, or authority rules change. Paste into Hermes (or another coding agent) with repo access.

---

## Prompt (copy from here)

```text
You are updating the Hermes operator skill for Continuity Forge.

## Goal
Produce a fully integrated agent skill that drives Continuity Forge’s **agentic** work through MCP (preferred) and REST (fallback), without ever owning canonical film state.

## Authority (hard constraints — never weaken)
1. Source screenplay is immutable input.
2. Deterministic kernel owns Production IR, continuity ledger, shot contracts, approvals, provenance.
3. Frontier-model / provider output is always PROPOSED until human-approved and committed.
4. Hermes must NOT treat chat memory, tool scratch, or workflow notes as canon.
5. Every mutating MCP/REST call needs: actor_id, authorization_scope, idempotency_key, rationale, and expected_state_hash when continuing prior state.
6. Write lease required for mutations (acquire before ingest/approvals; release after).
7. Controlled proof claim is always controlled_proof_not_production_ready for mock media.
8. No autonomous “director agent” that generates the whole film without shot contracts + validation gates.

## Inputs to read in-repo
- apps/mcp/src/continuity_forge_mcp/server.py (tool inventory)
- apps/api/src/continuity_forge_api/main.py (REST inventory)
- packages/repair/.../proof.py (controlled proof)
- AGENTS.md
- docs/architecture/PRODUCTION_HARNESS_ARCHITECTURE.md (Hermes section)
- docs/SETUP.md
- Existing skills/hermes-continuity-forge/**

## Deliverables (overwrite/update in place)
1. skills/hermes-continuity-forge/SKILL.md
   - YAML frontmatter: name, description with trigger phrases, when to use
   - Operating principles
   - Tool routing table (MCP tool → when)
   - Step-by-step workflows: controlled proof, lease+ingest, repair loop, drift audit, approval
   - Error / lease conflict handling
   - Completion receipt format for the human
2. skills/hermes-continuity-forge/references/mcp-tools.md — full tool list with args summary
3. skills/hermes-continuity-forge/references/mutation-contract.md — mutation envelope + lease rules
4. skills/hermes-continuity-forge/references/workflows.md — copy-paste operator sequences
5. docs/hermes/README.md — install paths for skill + MCP config
6. docs/hermes/mcp.example.json — absolute-path stdio example

## Style
- Imperative, short, checklist-friendly (agent skill, not marketing).
- Prefer MCP tools; mention REST equivalents only when useful (e.g. POST /v1/proof for one-shot receipt).
- Include concrete tool argument examples with placeholders.
- Do not invent tools that do not exist in server.py / main.py.

## Done when
- Skill would let Hermes run controlled proof and return a receipt without human writing raw JSON.
- Mutation paths always show lease + envelope fields.
- PROPOSED / not-production-ready language appears on generation paths.
```

---

## After the agent runs

1. Diff `skills/hermes-continuity-forge/` and `docs/hermes/`.
2. Run `make validate` if any code changed (docs-only is fine without).
3. Copy skill into Hermes skills dir and reload MCP.
4. Smoke: ask Hermes *“Run controlled proof on the continuity sample and summarize the receipt.”*
