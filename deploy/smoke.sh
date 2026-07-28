#!/usr/bin/env bash
# Lightweight smoke against a running API (compose or local uvicorn).
set -euo pipefail
BASE="${CF_SMOKE_BASE:-http://localhost:8080}"

echo "== health =="
curl -sf "$BASE/health" | tee /tmp/cf-health.json
echo

echo "== bootstrap dev tenant =="
KEY_JSON=$(curl -sf -X POST "$BASE/v1/tenants/bootstrap-dev")
echo "$KEY_JSON"
API_KEY=$(python -c 'import json,sys; print(json.load(sys.stdin)["api_key"])' <<<"$KEY_JSON")
AUTH=(-H "Authorization: Bearer $API_KEY")

echo "== whoami =="
curl -sf "${AUTH[@]}" "$BASE/v1/whoami"
echo

DOC="smoke-doc"
echo "== lease + ingest =="
curl -sf "${AUTH[@]}" -X POST "$BASE/v1/projects/lease" \
  -H 'Content-Type: application/json' \
  -d "{\"document_key\":\"$DOC\",\"holder\":\"smoke\"}"
echo

INGEST=$(curl -sf "${AUTH[@]}" -X POST "$BASE/v1/projects/ingest" \
  -H 'Content-Type: application/json' \
  -d "{\"document_key\":\"$DOC\",\"actor_id\":\"smoke\",\"authorization_scope\":\"kernel:pipeline\",\"idempotency_key\":\"smoke-1\",\"rationale\":\"smoke\",\"text\":\"INT. ROOM - DAY\\n\\nMara enters.\\n\\nMARA\\nGo.\\n\"}")
echo "$INGEST" | python -c 'import json,sys; d=json.load(sys.stdin); print("tenant", d["tenant_id"], "scenes", len(d["project"]["production_ir"]["scenes"]))'

SHOT=$(python -c 'import json,sys; d=json.load(sys.stdin); print(d["project"]["shot_contracts"]["contracts"][0]["shot_id"])' <<<"$INGEST")

echo "== generate preview =="
curl -sf "${AUTH[@]}" -X POST "$BASE/v1/generate/preview" \
  -H 'Content-Type: application/json' \
  -d "{\"document_key\":\"$DOC\",\"shot_id\":\"$SHOT\",\"seed\":\"smoke\",\"actor_id\":\"smoke\",\"authorization_scope\":\"generation:preview\",\"idempotency_key\":\"smoke-gen\",\"rationale\":\"smoke\"}" \
  | python -c 'import json,sys; d=json.load(sys.stdin); print(d["authority"], d["provider"], d["content_hash"][:12])'

echo "== controlled proof =="
curl -sf "${AUTH[@]}" -X POST "$BASE/v1/proof" \
  -H 'Content-Type: application/json' \
  -d "{\"document_key\":\"smoke-proof\",\"title\":\"Smoke\",\"seed\":\"smoke\",\"actor_id\":\"smoke\",\"text\":\"INT. ROOM - DAY\\n\\nMara enters with a red keycard.\\n\\nMARA\\nGo.\\n\\nEXT. ALLEY - NIGHT\\n\\nThe red keycard is gone.\\n\"}" \
  | python -c 'import json,sys; d=json.load(sys.stdin); assert d["claim"]=="controlled_proof_not_production_ready"; print(d["claim"], "shots", len(d["shots"]), "hash", d["receipt_hash"][:12])'

echo "== operator UI =="
curl -sf "$BASE/" | python -c 'import sys; t=sys.stdin.read(); assert "Proof workbench" in t; print("index ok")'
curl -sf "$BASE/tokens.css" | python -c 'import sys; t=sys.stdin.read(); assert "--color-accent" in t; print("tokens ok")'

echo "SMOKE OK"
