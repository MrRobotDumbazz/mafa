#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PORT="${FORTE_SELFCHECK_PORT:-8123}"
KEY="${FORTE_API_KEY:-selfcheck-key}"
VIDEO="${1:-../../datasets/open/videos/X-1.mov}"
[ -f "$VIDEO" ] || { echo "FAIL: video not found: $VIDEO"; exit 2; }

FORTE_PORT=$PORT FORTE_API_KEY=$KEY python3 -m app.main >/tmp/forte_selfcheck.log 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT

for i in $(seq 1 20); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break; sleep 0.5; done
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null || { echo "FAIL: health"; tail -n 20 /tmp/forte_selfcheck.log; exit 1; }
echo "ok: health"

CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:$PORT/api/v1/analyze" -F "file=@$VIDEO")
[ "$CODE" = "401" ] && echo "ok: 401 without key" || { echo "FAIL: expected 401, got $CODE"; exit 1; }

RESP=$(curl -sf -X POST "http://127.0.0.1:$PORT/api/v1/analyze" -H "X-API-Key: $KEY" -F "file=@$VIDEO")
JOB=$(printf '%s' "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
OUT=""
for i in $(seq 1 60); do
  OUT=$(curl -sf "http://127.0.0.1:$PORT/api/v1/jobs/$JOB" -H "X-API-Key: $KEY")
  ST=$(printf '%s' "$OUT" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  [ "$ST" != "processing" ] && break
  sleep 2
done
printf '%s' "$OUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['status'] == 'done', d
assert d['verdict'] in ('violation', 'no_violation'), d
for v in d.get('violations', []):
    assert v['evidence_frames'], v
    assert len(v['evidence_frames'][0]['image_base64']) > 1000, v
print('ok: job done | verdict:', d['verdict'], '| events:', len(d.get('violations', [])))
"

CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/api/v1/jobs/deadbeef" -H "X-API-Key: $KEY")
[ "$CODE" = "404" ] && echo "ok: 404 unknown job" || { echo "FAIL: expected 404, got $CODE"; exit 1; }

echo "SELFCHECK PASSED"
