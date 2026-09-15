# Optional Continuity Forge handoff

Creative work is standalone. For an explicitly requested canon handoff, load
`hermes-continuity-forge`, resolve the authorized document and actor, and confirm
MCP registration through repo `docs/hermes/README.md` (Python 3.12+; `docs/SETUP.md`).
No `ingest` subcommand exists in the Forge CLI. The CLI `compile` command is a
local deterministic parse/export, not a canonical project write.

Use `terminal(command="continuity-forge compile path/to/script.fountain --out path/to/ir.json")`
only for a reviewed output file. Compile Fountain/FDX screenplay source, not a
JSON scene contract, outline prose or symbolic packet. Preserve source as immutable input.

## MCP sequence

This Python-shaped recipe names MCP tools, not a new client library. Substitute
`DOC`, `ACTOR`, `SOURCE` and `INTENT` from the approved request; `INTENT` is a fresh
unique key per logical write, reused only for a retry of that identical intent.
Never import server persistence into an operator client. The server constructs
command_schema_version through MutationEnvelope; it is not an ingest_script argument.

```python
acquire_write_lease(document_key=DOC, holder=ACTOR, ttl_seconds=600)
try:
    prior = get_project_status(document_key=DOC)
    result = ingest_script(
        source=SOURCE,
        document_key=DOC,
        actor_id=ACTOR,
        authorization_scope="kernel:pipeline",
        idempotency_key=INTENT,
        rationale="Apply user-approved screenplay revision",
        title="Reviewed script",
        format="fountain",
        revision="0.1.0",
        expected_state_hash=prior["state_hash"] if prior else None,
    )
    status = get_project_status(document_key=DOC)
    assert status is not None
    assert status["state_hash"] == result["project"]["state_hash"]
finally:
    release_write_lease(document_key=DOC, holder=ACTOR)
```

Acquire must succeed before entering the try/finally; never release someone else's
lease. Stop on conflicts, stale hashes, failed schema validation or incomplete
read-back. Keep the full result, document key, run ID, scene/shot IDs and hashes.
Future revisions use fresh project `state_hash`, not a pipeline shots hash.

## Narrative and symbolic packets

Briefs, character bibles, scene contracts, symbolic_architecture and cinematic_encoding
are **PROPOSED attachments for review**, not guaranteed compiler inputs or supported
IR fields. No automatic motif/geometry field mapping is promised. Check the actual
kernel models and round-trip returned schemas before claiming a constraint was
stored. The deterministic kernel alone owns approved identity, ledger, IR and shot
contracts; a narrative skill or model cannot promote attachments into canon.

## Verification without live writes

From a full checkout, use `terminal(command="python -m pytest tests/test_authored_skill_recipes.py tests/contract/test_mcp.py -q")`.
Tests bind this exact recipe to real MCP signatures with a fresh in-memory runtime
and mock provider; no external service, credentials or live approval is involved.
