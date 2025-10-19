# Repository Guidelines

## Project Structure & Module Organization
- Back-end services live under `services/`: FastAPI API in `services/api/`, asynchronous jobs in `services/dj-worker/`, and the chatterbox proxy in `services/chatterbox-shim/`.
- The React UI lives in `web/`; the seasonal variant ships from `web-christmas/`. Build artifacts sit in each package’s `dist/` directory.
- Streaming and runtime configs live under `infra/` and `infra/liquidsoap/`. Shared audio assets are mounted through `shared/music/`, `shared/tts/`, and logs stream into `logs/`.
- Station metadata and scripts belong in `stations.yml` and `scripts/` respectively; align new modules with the existing service-based layout.

## Build, Test, and Development Commands
- `make setup` seeds `.env` files and creates required local directories on first run.
- `make build` builds every container image; `make up` and `make up-dev` start the full stack (prod vs. dev defaults).
- `make status` and `make health` provide container status and health hints; `make logs-<service>` tails individual services (`make logs-api`, `make logs-dj`, etc.).
- Run targeted scripts via `docker compose exec <service> <command>` when inspecting containers directly.

## Coding Style & Naming Conventions
- Python uses 4-space indents, type hints, and Ruff; run `ruff check` and `ruff format` before committing.
- The frontend uses TypeScript, Vite, Tailwind, and ESLint with 2-space indents; enforce style with `npm run lint:fix` within `web/` or `web-christmas/`.
- Name branches `feature/<slug>`, `fix/<slug>`, or `chore/<slug>`; Python modules stay `snake_case.py`, React components use `PascalCase.tsx`.

## Testing Guidelines
- Python tests live alongside services in `services/<service>/tests/`; execute via `docker compose exec api pytest -q` or the DJ worker equivalent.
- Frontend tests reside in `web/src/__tests__/`; run with `cd web && npm test` (or `web-christmas` as needed).
- Favor descriptive test names and keep fixtures close to their targets; add coverage for every new behavior before opening a PR.

## Commit & Pull Request Guidelines
- Write commits in imperative tense with scoped prefixes, e.g., `api: add now-playing endpoint`; include the relevant service in the prefix.
- PRs should summarize the change, link issues, note migrations/config updates, attach screenshots for UI work, and list the test commands executed.
- Confirm `make lint` and `make format` pass locally before requesting review.

## Security & Configuration Tips
- Store secrets in `.env` files derived from `.env.example`; never commit secrets.
- On low-resource hosts set `DJ_PROVIDER=templates` (or `disabled`) and `MAX_CONCURRENT_JOBS=1`; monitor `docker stats` during load.
- Review `SYSTEM_PROTECTION.md` before shipping infrastructure changes, and keep generated TTS output inside `shared/tts/`.
