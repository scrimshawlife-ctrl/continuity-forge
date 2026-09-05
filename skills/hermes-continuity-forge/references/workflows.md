# Operator workflows (copy sequences)

Replace placeholders: `{{DOC}}`, `{{ACTOR}}`, `{{SOURCE}}`, `{{SHOT}}`.

---

## 1. Shot breakdown handoff (default — structure + continuity)

### MCP

```text
build_breakdown(
  source="{{SOURCE}}",
  title="…",
  document_key="{{DOC}}",
  format="fountain"
)
# optional: build_breakdown_markdown(...) for human export
```

### REST

```http
POST /v1/breakdown
Content-Type: application/json

{
  "title": "My Script",
  "document_key": "{{DOC}}",
  "text": "{{SOURCE}}",
  "format": "fountain"
}
```

Summarize: `claim`, `package_hash`, `shot_count`, `entity_count`, first sluglines.  
Schema: `cf.breakdown.v1`. Not production film.

---

## 2. Controlled proof via REST (optional mock media)

```http
POST /v1/proof
Content-Type: application/json

{
  "title": "Continuity Sample",
  "document_key": "{{DOC}}",
  "text": "{{SOURCE}}",
  "format": "fountain",
  "seed": "proof",
  "actor_id": "{{ACTOR}}",
  "budget_seconds": 60
}
```

Summarize JSON: claim, hashes, shots[].status / attempts / repair_actions.

---

## 3. Ingest under lease (MCP)

Use the exact try/finally ingest recipe in the writing skills' integration guide.
This complete sequence uses freshly read project state (not a pipeline shots hash):

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
        expected_state_hash=prior["state_hash"] if prior else None,
    )
    status = get_project_status(document_key=DOC)
    assert status["state_hash"] == result["project"]["state_hash"]
finally:
    release_write_lease(document_key=DOC, holder=ACTOR)
```

## 4. Candidate generation / repair (MCP)

Resolve SHOT from the project's stored contracts. ACTOR is stable; INTENT and
REPAIR_INTENT are distinct, fresh per logical operation (reused only on retries).
These calls may write candidate artifacts but do not acquire a canon lease.
Pass the freshly read project `state_hash` as `expected_state_hash` (not a shot or
pipeline hash). The server validates it before generation and persistence while
holding the runtime project-store lock. Omission binds to a server-read snapshot,
not to an earlier client review. On conflict, re-read and review before retrying.
The server constructs command_schema_version; do not pass that argument.
This lock coordinates a single store instance; it is not a distributed lease
across independently hydrated filesystem/Postgres runtimes.

```python
before = get_project_status(document_key=DOC)
candidate = queue_generation(
    document_key=DOC,
    shot_id=SHOT,
    actor_id=ACTOR,
    authorization_scope="generation:preview",
    idempotency_key=INTENT,
    rationale="User requested mock preview",
    expected_state_hash=before["state_hash"],
    seed="hermes-1",
)
repair = run_shot_repair_loop(
    document_key=DOC,
    shot_id=SHOT,
    actor_id=ACTOR,
    authorization_scope="generation:repair",
    idempotency_key=REPAIR_INTENT,
    rationale="User requested bounded mock repair",
    expected_state_hash=before["state_hash"],
    seed="hermes-1",
    max_attempts=3,
    fail_first=False,
)
after = get_project_status(document_key=DOC)
assert before["state_hash"] == after["state_hash"]
```

Verify returned shot IDs, candidate authority=PROPOSED, validation/status and actual
attempts; do not claim an accepted_candidate exists if repair failed. There is no
public MCP candidate fetch tool. Return-payload checks plus unchanged canon are
not read-back of persisted candidate storage; label that limit explicitly.

---

## 5. Drift audit (MCP)

```text
1. get_project_status("{{DOC}}")
2. audit_drift("{{DOC}}")
3. inspect_character_state("{{DOC}}", "Mara")  # example
4. resolve_resource("cf://projects/{{DOC}}/continuity-ledger")
```

---

## 6. Human approval via REST

```text
1. acquire lease as {{ACTOR}}
2. POST /v1/approvals/request  { document_key, kind, actor_id, idempotency_key, rationale }
3. POST /v1/approvals/decide   { approval_id, status: granted|denied, … }
4. GET /v1/projects/{key}/approvals — match exact approval_id and status
5. release the acquired lease in finally (including errors)
```

Only when the human explicitly requests grant/deny for the kind in scope.
