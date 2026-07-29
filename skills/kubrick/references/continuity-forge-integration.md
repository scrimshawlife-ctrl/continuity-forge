# Continuity Forge Integration

This skill is the **creative / structural** layer. Continuity Forge is the **deterministic kernel** that owns canonical state.

## When to Handoff

- After premise, characters, structure, or scene contracts are approved by the user.
- Before or instead of writing full prose pages when the goal is production use.
- On any material change to canon (new approved scenes, character traits that affect continuity, structure revisions).

## Recommended Handoff Flow

1. Produce clean artifacts from this skill (project brief, scene contracts, character bibles, approved canon list, symbolic_architecture and cinematic_encoding when applicable).
2. Ingest via Forge (prefer MCP or CLI with proper mutation envelope):
   - `acquire_write_lease`
   - `ingest_script` (or `compile_script` + ingest)
   - `build_ledger` / `build_shot_contracts`
3. Capture receipt (hashes, document_key, shot IDs).
4. Reference Forge state in future work (use `get_project_status`, `inspect_scene`, etc. for grounding).

## CLI Examples

```bash
# Basic compile from fountain or structured text
continuity-forge compile path/to/outline.fountain --out out/

# Or from a scene contract / brief you produced here
continuity-forge ingest --document-key myfilm --source structured-outline.md
```

## MCP Tools (via companion `hermes-continuity-forge` skill)

Typical tools you will call after creative work:
- `compile_script`
- `ingest_script` (with mutation contract)
- `build_ledger`
- `build_shot_contracts`
- `get_project_status`
- `audit_drift`

Always include:
- `document_key`
- `actor_id` (e.g. hermes-kubrick-<session>)
- Full mutation envelope when writing

## Mutation Contract Requirements (when ingesting changes)

From the operator skill:
- actor_id
- authorization_scope
- idempotency_key
- rationale
- expected_state_hash (when updating existing)

This skill produces the *rationale* and *content*. The operator skill (or direct MCP call) supplies the envelope.

## Boundaries

- This skill may generate **PROPOSED** narrative material and scene contracts (including symbolic proposals).
- Forge owns the canonical ledger, IR, and shot contracts.
- Never claim "this is now in the film" until you have a Forge receipt with committed status.
- For drift or contradictions discovered here: run local CONTINUITY pass, then cross-validate with Forge `audit_drift`.

## Recommended Pairing

Load both skills:
- `kubrick` for creative development, diagnosis, anti-slop, voice, structure, symbolic dramaturgy and cinematic encoding.
- `hermes-continuity-forge` for leases, ingestion, proof, shot repair, approvals.

See main repo `docs/hermes/README.md` and the companion skill for full operator rules.
