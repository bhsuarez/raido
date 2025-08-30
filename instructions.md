Raido Dev and Prod Runbook

Overview
- Dev uses Vite on port 3000 inside the `web` container and Caddy maps host 3000 → Vite.
- API runs with hot-reload on port 8001 (host) via docker-compose override.
- Stream (Icecast) and Liquidsoap run as usual.

Quick Start (Dev)
1) Stop any running stack
   - docker compose -f docker-compose.yml -f docker-compose.override.yml down --remove-orphans
2) Start stream services
   - docker compose -f docker-compose.yml -f docker-compose.override.yml up -d icecast liquidsoap
3) Start API (hot reload) and Web (Vite)
   - docker compose -f docker-compose.yml -f docker-compose.override.yml up -d --no-deps api web-dev proxy
4) Open
   - Frontend: http://localhost:3000 (served via Caddy → Vite)
   - API: http://localhost:8001 (health at /health)
   - Now Playing API: http://localhost:8001/api/v1/now/
   - Stream: http://localhost:8000/stream/raido.mp3

Typical Dev Loop
- Frontend changes (web/src): Auto hot-reload via Vite.
- Frontend config/deps changed (vite.config.ts, package.json):
  - docker compose -f docker-compose.yml -f docker-compose.override.yml restart web-dev
- Backend changes (services/api/app): Auto reload via uvicorn --reload.
- Backend deps changed (services/api/requirements.txt):
  - docker compose build api && docker compose -f docker-compose.yml -f docker-compose.override.yml up -d api

Rebuild Frontend (Prod image)
- docker compose build web
- To run full prod stack behind Caddy (port 3000):
  1) docker compose -f docker-compose.yml -f docker-compose.override.yml down --remove-orphans
  2) docker compose -f docker-compose.yml up -d proxy api web icecast liquidsoap
  3) Open http://localhost:3000

Notes on DB
- In dev, API now starts even if DB is unavailable. Now Playing falls back to Liquidsoap.
- To enable DB:
  - docker compose -f docker-compose.yml -f docker-compose.override.yml up -d db
- If you previously saw Postgres "ContainerConfig" errors, clean and re-pull:
  - docker compose down -v
  - docker image rm postgres:16 || true
  - docker system prune -af
  - docker compose pull db
  - docker compose up -d db

Troubleshooting
- White screen at http://localhost:3000
  - Ensure proxy+web up: docker compose -f docker-compose.yml -f docker-compose.override.yml ps
  - View logs:
    - docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f proxy
    - docker compose -f docker-compose.yml -f docker-compose.override.yml logs -f web
- Now playing not loading
  - API reachable: curl http://localhost:8001/health
  - Endpoint: curl http://localhost:8001/api/v1/now/
  - Liquidsoap up: docker compose -f docker-compose.yml -f docker-compose.override.yml up -d liquidsoap
- Frontend doesn’t hot reload
  - Restart web: docker compose -f docker-compose.yml -f docker-compose.override.yml restart web
  - Vite host allowlist includes localhost; ensure you’re on http://localhost:3000

One-liners
- Full dev restart (no DB):
  - docker compose -f docker-compose.yml -f docker-compose.override.yml down --remove-orphans && \
    docker compose -f docker-compose.yml -f docker-compose.override.yml up -d icecast liquidsoap api web-dev proxy
- Rebuild web prod image:
  - docker compose build web && docker compose up -d web
