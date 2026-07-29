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

```text
1. acquire_write_lease(document_key="{{DOC}}", holder="{{ACTOR}}", ttl_seconds=600)
2. ingest_script(
     source="{{SOURCE}}",
     document_key="{{DOC}}",
     actor_id="{{ACTOR}}",
     authorization_scope="kernel:pipeline",
     idempotency_key="ingest-{{DOC}}-{{unique}}",
     rationale="Hermes operator ingest",
     title="…",
     format="fountain"
   )
3. get_project_status("{{DOC}}")
4. release_write_lease("{{DOC}}", "{{ACTOR}}")
```

---

## 4. Repair one shot (MCP)

```text
1. list_shot_summaries(source=…) OR use stored project contracts after ingest
2. run_shot_repair_loop(
     document_key="{{DOC}}",
     shot_id="{{SHOT}}",
     seed="hermes-1",
     max_attempts=3,
     fail_first=false
   )
3. Report authority=PROPOSED, status, attempts, repair plan
```

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
4. release lease
```

Only when the human explicitly requests grant/deny for the kind in scope.
