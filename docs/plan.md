Build Plan (Phased)

Phase 0 – Bootstrap
	•	Private repo, .env.example, docker compose skeleton
	•	Postgres migrations ready

Phase 1 – Core Stream
	•	Icecast + Liquidsoap playing /music
	•	Parse Liquidsoap HTTP status in backend
	•	DB tables in place

Phase 2 – AI DJ Worker
	•	Backend → commentary queue
	•	Worker → OpenAI/Ollama + TTS providers
	•	Store commentary clips in /shared/tts

Phase 3 – Frontend + WS
	•	React: Now/Next/History, progress bar
	•	Album art lookup
	•	Transcripts & audio panel

Phase 4 – Admin + Security
	•	OIDC login, JWT
	•	Settings editor
	•	HTTPS via proxy

Phase 5 – Observability & Hardening
	•	OpenTelemetry, Prometheus
	•	Backups + redacted logs

Stretch goals: BPM-aware transitions, listener chat, dedup heuristics.
