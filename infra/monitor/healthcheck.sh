#!/bin/sh

# Simple in-stack health monitor with optional Slack webhook alerts.
# Reads ALERT_SLACK_WEBHOOK from environment if set.

set -eu

API_URL="http://api:8000/health"
WEB_URL="http://web:3000/health"
STREAM_URL="http://icecast:8000/stream/raido.mp3"
INTERVAL_SECONDS="60"

log() { echo "[monitor] $(date -Iseconds) $*"; }

notify_slack() {
  [ -z "${ALERT_SLACK_WEBHOOK:-}" ] && return 0
  title="$1"
  text="$2"
  payload=$(printf '{"text":"%s"}' "*Raido Alert:* ${title}\n${text}" | sed 's/"/\\"/g')
  # shellcheck disable=SC2086
  curl -s -X POST -H 'Content-type: application/json' --data "${payload}" "$ALERT_SLACK_WEBHOOK" >/dev/null 2>&1 || true
}

check_api() {
  status=$(curl -sS --max-time 5 "$API_URL" | grep -o '"status":"[^"]*"' || true)
  if [ -z "$status" ]; then
    notify_slack "API healthcheck failed" "GET ${API_URL} did not return status"
    log "API: FAIL"
    return 1
  fi
  log "API: OK ($status)"
}

check_web() {
  if curl -sS --max-time 5 "$WEB_URL" >/dev/null; then
    log "Web: OK"
  else
    notify_slack "Web healthcheck failed" "GET ${WEB_URL} non-200"
    log "Web: FAIL"
    return 1
  fi
}

check_stream() {
  # Try to fetch first byte; success if 2xx
  if curl -sS --fail --max-time 5 -r 0-0 "$STREAM_URL" -o /dev/null; then
    log "Stream: LIVE"
  else
    notify_slack "Stream offline" "HEAD/GET ${STREAM_URL} failed"
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

