## Summary

Beta readiness improvements:
- Fix Makefile health checks (API on host port 8001; robust stream check)
- Correct dj-worker healthcheck to target `api:8000` intra-network
- Add lightweight `monitor` service that checks API/Web/Stream every 60s
- Optional Slack alerts via `ALERT_SLACK_WEBHOOK`
- Update README and `.env.example`

## Motivation

Ensure core services are monitored and obvious misconfigurations are avoided; reduce time-to-detect when the stream or API becomes unavailable.

## Changes

- Makefile: health target updates
- docker-compose.yml: dj-worker healthcheck fix; new monitor service
- infra/monitor/healthcheck.sh: monitor script
- .env.example: add `ALERT_SLACK_WEBHOOK`
- README: monitoring section and port clarifications

## Testing

- Ran `make health` locally: API and Web OK; Stream reflects live/offline correctly.
- `docker-compose ps` shows all services Up; monitor starts and logs checks.

## Deploy Notes

- Optional: set `ALERT_SLACK_WEBHOOK` in `.env` to enable alerts.
- For dev: API is exposed on `localhost:8001` (as per override compose).

## Screenshots / Logs

- N/A (monitor logs show periodic checks, alerts sent when configured)

## Checklist

- [ ] Secrets and tokens are not committed
- [x] Lint and format pass
- [x] Changes are scoped and documented

