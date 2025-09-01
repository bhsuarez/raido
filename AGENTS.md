# Repository Guidelines

## Project Structure & Module Organization
- `services/api/`: FastAPI backend (DB, schemas, routes, websockets).
- `services/dj-worker/`: Background jobs: commentary, TTS, integrations.
- `web/`: React + TypeScript UI (Vite, Tailwind, ESLint).
- `infra/liquidsoap/`: Liquidsoap streaming configs and helpers.
- `shared/`: Volumes (`shared/music`, `shared/tts`, `shared/logs`).
- `logs/`: Runtime logs (e.g., Icecast).
- `kokoro-tts/`: Local TTS tooling/assets.

## Build, Test, and Development Commands
- `make setup`: Copy `.env.example` → `.env`, create required dirs.
- `make build`: Build Docker images; `make up` / `make up-dev` start the stack.
- `make status` / `make health`: Container status and basic service checks.
- `make logs[-api|-dj|-web|-liquidsoap]`: Tail service logs.
- `make migrate` | `make migrate-create name=<msg>`: DB migrations.
- `make lint` | `make format`: Lint and auto-format backend/frontend.
- Dev URLs: API `http://localhost:8000`, Web `http://localhost:3000`, Stream `http://localhost:8000/stream/raido.mp3`.

## Coding Style & Naming Conventions
- Python: 4 spaces, type hints preferred; run `ruff check` and `ruff format`.
- Web: TypeScript + ESLint; fix with `npm run lint:fix`. 2-space indent.
- Names: Branches `feature/<slug>`, `fix/<slug>`, `chore/<slug>`.
- Files: Python `snake_case.py`; React components `PascalCase.tsx`.

## Testing Guidelines
- API/DJ: Place Pytest tests under `services/<service>/tests/`.
- Web: Put Jest/Vitest tests under `web/src/__tests__/`.
- Until `make test` is wired, run directly, e.g.: `docker compose exec api pytest -q` and `cd web && npm test`.

## Commit & Pull Request Guidelines
- Commits: Imperative, scoped prefix (e.g., `api: add now-playing endpoint`).
- PRs: Include summary, linked issues, test steps, and UI screenshots where relevant; call out migrations/config changes.
- Pre-merge: `make lint`, `make format`, boot with `make up-dev`, verify no secrets in diffs.

## Security & Configuration Tips
- Keep secrets in `.env` (see `.env.example`); never commit secrets.
- Media: put audio in `shared/music/`; generated TTS in `shared/tts/`.
- See `SYSTEM_PROTECTION.md` for safety constraints and guardrails.

## Incident: Service Overload (Host Reboot Required)

- Summary: Host became unresponsive due to sustained CPU saturation from the DJ worker triggering frequent AI commentary generation while protections were disabled. A reboot was required to recover.

- Impact: High CPU load across containers (Ollama, dj-worker, API), degraded responsiveness, stream interruptions, and eventual host instability.

- Root Cause:
  - System protection in the DJ worker was disabled (import of `system_monitor` was commented out), so load-based backoff never engaged.
  - Admin defaults returned `dj_provider=ollama`, which drives on‑host LLM inference; combined with `WORKER_POLL_INTERVAL=5` and `MAX_CONCURRENT_JOBS=3` this allowed repeated/parallel generations under load.
  - Web/API polling of now/next endpoints adds Liquidsoap telnet calls and occasional artwork lookups, compounding CPU and I/O when under stress.

- Evidence Observed:
  - `services/dj-worker/app/worker/dj_worker.py` had `system_monitor = None` with the protective import commented out.
  - Admin settings schema defaulted to `dj_provider=ollama`, enabling CPU-bound inference by default when DB settings are empty.
  - Icecast logs show stream interruptions around the incident window; SYSTEM_PROTECTION.md references prior overload modes consistent with this pattern.

- Fix Implemented:
  - Re-enabled system protection in DJ worker by importing `system_monitor` (file: `services/dj-worker/app/worker/dj_worker.py`).
  - Tuned safer worker defaults (file: `services/dj-worker/app/core/config.py`):
    - `WORKER_POLL_INTERVAL`: 10s
    - `MAX_CONCURRENT_JOBS`: 1
  - Made safer admin default (file: `services/api/app/schemas/admin.py`): `dj_provider=templates` to prefer light, deterministic generation unless explicitly changed in the UI.

- Recommended Config Changes (ops):
  - Set `DJ_PROVIDER=templates` or `disabled` in `.env` for low‑resource environments; enable Ollama only when capacity is available.
  - If using Ollama, pin a small model and keep concurrency at 1.
  - Optionally add Docker resource limits for `ollama` and `dj-worker` (CPU shares/quotas, memory limits).

## Provider Options

- Commentary `dj_provider` (text): `openai`, `ollama`, `templates`, `disabled`.
- Voice `dj_voice_provider` (TTS): `kokoro`, `xtts`, `liquidsoap`, `openai_tts`.
- Typical combos:
  - Lightweight: `templates` + `kokoro`
  - Local LLM: `ollama` + (`kokoro` or `xtts`)
  - Fully disabled: `disabled` (voice ignored)

- Runbook (stabilize + verify):
  - Disable heavy generation fast: set `DJ_PROVIDER=disabled` and restart `dj-worker`.
  - Confirm protections active: tail dj-worker logs for health/circuit messages.
  - Gradually re‑enable: switch to `templates` first; if stable, consider `ollama` with concurrency=1.
  - Monitor: `docker stats`, `uptime`, `free -h`, and API `/api/v1/admin/tts-status`.

- Next Steps (optional hardening):
  - Add API rate limiting or caching on now/next endpoints.
  - Add per‑minute max generation guard in DJ worker (soft throttle).
  - Add compose resource limits for `ollama`.
