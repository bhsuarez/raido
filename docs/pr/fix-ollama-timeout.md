Title: dj-worker: increase Ollama HTTP timeout to reduce ReadTimeouts under load

Summary
- Increase Ollama HTTP client timeout from 30s to 60s in dj-worker to reduce intermittent ReadTimeout failures during commentary generation on constrained hosts or when the model is cold-starting.

Changes
- services/dj-worker/app/services/ollama_client.py
  - Bump httpx AsyncClient timeout from 30.0 to 60.0 seconds.

Context
- During periods of higher load or model cold starts, Ollama requests were timing out at ~30s, causing commentary generation to fail. When text generation fails, no TTS is produced, leading to gaps on-air.
- Logs showed repeated `Ollama commentary generation failed` with `ReadTimeout`.

Validation
- Build dj-worker and restart.
- Set `dj_provider=ollama` and confirm Admin has a custom prompt.
- Observe dj-worker logs: should show `Using custom DJ prompt template` and successful response instead of timeouts.
- If timeouts persist:
  - Lower `dj_max_tokens` (e.g., 120–160) in Admin settings to keep responses short.
  - Ensure Ollama model is small (`llama3.2:1b`) and loaded.

Operational Notes
- This change does not alter defaults in Admin or DB; it only increases the client timeout window.
- For low-resource hosts, consider `dj_provider=templates` or single-model, concurrency=1 for Ollama.

