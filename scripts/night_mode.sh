#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[night_mode] Disabling DJ provider (night override) and recreating dj-worker..."
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  -f docker-compose.night.yml \
  up -d --no-deps --force-recreate dj-worker

# Also disable at the API level so admin settings override env can't re-enable
API_URL=${API_URL:-http://localhost:8001}
echo "[night_mode] Posting admin settings to disable commentary at ${API_URL}..."
curl -sS -X POST "${API_URL}/api/v1/admin/settings" \
  -H 'Content-Type: application/json' \
  -d '{"dj_provider":"disabled","enable_commentary":false}' || true

echo "[night_mode] Done. Current dj-worker environment (DJ_*, *_PROVIDER):"
docker exec raido-dj-worker-1 /bin/sh -lc 'printenv | sort | egrep -i "^DJ_|_PROVIDER|OLLAMA_NUM_PARALLEL"' || true
