#!/usr/bin/env bash
# Connector smoke: hit breakdown API like an integrator would.
# Usage:
#   ./scripts/connector_smoke.sh
#   CF_API_BASE=http://127.0.0.1:8080 ./scripts/connector_smoke.sh
#   ./scripts/connector_smoke.sh /path/to/script.fountain
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${CF_API_BASE:-http://127.0.0.1:8080}"
FIXTURE="${1:-$ROOT/tests/golden/fixtures/continuity.fountain}"

if [[ ! -f "$FIXTURE" ]]; then
  echo "FAIL: fixture not found: $FIXTURE" >&2
  exit 1
fi

STEM=$(basename "$FIXTURE")
STEM=${STEM%.*}

BODY=$(python3 - <<PY
import json
path = "$FIXTURE"
text = open(path, encoding="utf-8").read()
print(json.dumps({
    "title": "$STEM",
    "document_key": "connector-smoke-$STEM",
    "format": "fdx" if path.lower().endswith(".fdx") else "fountain",
    "text": text,
}))
PY
)

echo "==> GET $BASE/health"
HEALTH=$(curl -sf "$BASE/health")
echo "$HEALTH"
echo "$HEALTH" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("status")=="ok", d'

echo "==> POST $BASE/v1/breakdown"
RESP=$(curl -sf "$BASE/v1/breakdown" \
  -H 'Content-Type: application/json' \
  -d "$BODY")
echo "$RESP" | python3 - <<'PY'
import json, sys
d = json.load(sys.stdin)
assert d.get("schema_version") == "cf.breakdown.v1", d.get("schema_version")
assert d.get("shot_count", 0) >= 1, d
assert d.get("package_hash"), "missing package_hash"
print(f"  OK  shots={d['shot_count']} entities={d['entity_count']} package_hash={d['package_hash'][:16]}…")
print(f"  claim={d.get('claim')}")
PY

echo "==> connector smoke PASS"
echo "  Point integrators at POST /v1/breakdown (cf.breakdown.v1). Not production film."
