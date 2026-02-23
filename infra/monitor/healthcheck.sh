#!/bin/sh

# Simple in-stack health monitor with Pingos (Matrix) alerts.

set -eu

API_URL="http://api:8000/health"
WEB_URL="http://web/health"
STREAM_URL="http://icecast:8000/raido.mp3"
PINGOS_URL="http://192.168.1.116:8090/api/notify"
INTERVAL_SECONDS="60"

log() { echo "[monitor] $(date -Iseconds) $*"; }

notify() {
  title="$1"
  text="$2"
  msg="🚨 Raido Alert: ${title} — ${text}"
  payload=$(printf '{"message":"%s"}' "$msg")
  curl -s -X POST -H 'Content-Type: application/json' --data "$payload" "$PINGOS_URL" >/dev/null 2>&1 || true
}

check_api() {
  status=$(curl -sS --max-time 5 "$API_URL" | grep -o '"status":"[^"]*"' || true)
  if [ -z "$status" ]; then
    notify "API healthcheck failed" "GET ${API_URL} did not return status"
    log "API: FAIL"
    return 1
  fi
  log "API: OK ($status)"
}

check_web() {
  if curl -sS --max-time 5 "$WEB_URL" >/dev/null; then
    log "Web: OK"
  else
    notify "Web healthcheck failed" "GET ${WEB_URL} non-200"
    log "Web: FAIL"
    return 1
  fi
}

check_stream() {
  # For live streams, curl will time out (exit 28) even when data is flowing.
  # Accept exit 0 or 28; anything else (e.g. connection refused) is a real failure.
  bytes=$(curl -sS -o /dev/null --max-time 3 -w "%{size_download}" "$STREAM_URL" 2>/dev/null || true)
  if [ -n "$bytes" ] && [ "$bytes" -gt 0 ]; then
    log "Stream: LIVE (${bytes} bytes)"
  else
    notify "Stream offline" "GET ${STREAM_URL} returned no data"
    log "Stream: OFFLINE"
    return 1
  fi
}

log "Starting health monitor; interval=${INTERVAL_SECONDS}s"
while true; do
  failures=0
  check_api || failures=$((failures+1))
  check_web || failures=$((failures+1))
  check_stream || failures=$((failures+1))
  if [ "$failures" -gt 0 ]; then
    log "Failures detected: $failures"
  fi
  sleep "$INTERVAL_SECONDS"
done
