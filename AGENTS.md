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
