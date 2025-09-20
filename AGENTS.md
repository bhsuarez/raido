# Repository Guidelines

## Project Structure & Module Organization
The stack is split by service. FastAPI lives in `services/api/` (routes, schemas, websockets); background jobs run from `services/dj-worker/`; the React UI is in `web/`. Streaming configs sit under `infra/liquidsoap/`, and shared volumes for music, TTS, and logs live in `shared/`. Use `logs/` for runtime output and `kokoro-tts/` for local voice assets.

## Build, Test, and Development Commands
Run `make setup` once to seed env files and required directories. Use `make build` to build all container images, then `make up` or `make up-dev` to launch the stack. Check status with `make status` or health hints via `make health`. Tail service-specific logs (`make logs-api`, `make logs-dj`, etc.) while debugging.

## Coding Style & Naming Conventions
Python follows 4-space indents, type hints, and Ruff (`ruff check`, `ruff format`). The web app uses TypeScript, Vite, Tailwind, and ESLint with 2-space indents; fix issues with `npm run lint:fix`. Name branches `feature/<slug>`, `fix/<slug>`, or `chore/<slug>`; Python modules use `snake_case.py`, React components use `PascalCase.tsx`.

## Testing Guidelines
Place Pytest suites under `services/<service>/tests/`; run via `docker compose exec api pytest -q` or the dj-worker equivalent. Frontend tests live in `web/src/__tests__/`; execute `cd web && npm test`. Keep tests close to implementation, favor descriptive test names, and ensure new behavior has coverage before opening a PR.

## Commit & Pull Request Guidelines
Write commits in imperative tense with scoped prefixes (e.g., `api: add now-playing endpoint`). PRs should summarize the change, link issues, document migrations or config updates, include relevant screenshots, and note test commands executed. Confirm `make lint` and `make format` pass before requesting review.

## Security & Configuration Tips
Store secrets in `.env` (derive from `.env.example`). For low-resource hosts set `DJ_PROVIDER=templates` or `disabled`, keep `MAX_CONCURRENT_JOBS=1`, and monitor `docker stats` during high load. Use `SYSTEM_PROTECTION.md` as the guardrail reference, and place audio assets in `shared/music/` with generated TTS in `shared/tts/`.

## Chatterbox Shim & TTS Flow
`services/chatterbox-shim/` proxies commentary TTS to the upstream server at `http://192.168.1.112:8000`. The DJ worker posts to `{CHATTERBOX_BASE_URL}/api/speak` with `text` and `voice_id`; the shim forwards to `/v1/audio/speech` (fallback `/tts`), stores the returned audio under `/shared/tts/commentary_*.mp3`, and the API injects it via `tts.push`. Validate the shim with `curl http://localhost:18000/health`, then issue `curl -s -X POST http://localhost:18000/api/speak -H 'Content-Type: application/json' -d '{"voice_id":"cb231744-e7c6-4f56-9aaa-593720b38928","text":"Test line"}' > /tmp/test.mp3` to confirm audio output. Tail `docker compose logs chatterbox-shim` or `docker compose logs dj-worker` if jobs stall.
