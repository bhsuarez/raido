#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[day_mode] Enabling normal DJ provider (from .env) and recreating dj-worker..."
docker compose \
  -f docker-compose.yml \
  -f docker-compose.override.yml \
  up -d --no-deps --force-recreate dj-worker

# Also enable at the API level to ensure admin settings match desired daytime mode
API_URL=${API_URL:-http://localhost:8001}
DAY_PROVIDER=${DAY_PROVIDER:-templates}
echo "[day_mode] Posting admin settings to enable commentary at ${API_URL} (provider=${DAY_PROVIDER})..."
curl -sS -X POST "${API_URL}/api/v1/admin/settings" \
  -H 'Content-Type: application/json' \
  -d "{\"dj_provider\":\"${DAY_PROVIDER}\",\"enable_commentary\":true}" || true

echo "[day_mode] Done. Current dj-worker environment (DJ_*, *_PROVIDER):"
docker exec raido-dj-worker-1 /bin/sh -lc 'printenv | sort | egrep -i "^DJ_|_PROVIDER|OLLAMA_NUM_PARALLEL"' || true
