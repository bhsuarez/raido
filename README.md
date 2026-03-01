# Raido - AI Radio

A 24/7 AI-powered radio station with live DJ commentary.

<img width="600" alt="Now Playing" src="https://github.com/user-attachments/assets/250aa1b2-3878-47c8-a64a-c8fdebae001a" />

## Stack

- **FastAPI** — REST API + WebSocket
- **React/TypeScript** — web frontend (Vite)
- **PostgreSQL** — track history, settings
- **Liquidsoap** — audio mixing engine
- **Icecast** — stream broadcast
- **Caddy** — reverse proxy
- **Ollama** — local LLM for DJ commentary
- **Chatterbox / Kokoro / OpenAI** — TTS options

## Infrastructure (PCT 127)

| Component | Location |
|-----------|----------|
| Host | PCT 127 (`192.168.1.41`) |
| Docker Compose | `/opt/raido/docker-compose.yml` |
| Music library | `/mnt/music` |
| DB data | `/mnt/raido-db` (ZFS bind mount) |
| Git remote | `raido` → `https://github.com/bhsuarez/raido.git` |

## Deploy

```bash
# Always deploy after pushing to main
pct exec 127 -- bash -c "cd /opt/raido && git pull raido main"
pct exec 127 -- bash -c "cd /opt/raido && docker compose build api web mb-enricher"
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d"
```

## Quick Start (fresh install)

```bash
make setup      # Copy .env, create directories
make build      # Build all containers
make up         # Start services
make migrate    # Run DB migrations

# Scan music library
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"
curl -X POST "http://localhost:8001/api/v1/artwork/batch_extract?limit=100"
```

## Access Points

| URL | What |
|-----|------|
| `http://localhost` | Web UI |
| `http://localhost/raido/admin` | DJ Admin |
| `http://localhost/api/v1` | API (via proxy) |
| `http://localhost:8000/raido.mp3` | Stream |
| `/docs` | Swagger UI |

---

## Architecture

```
Matrix message
React Web UI ──► FastAPI ──► PostgreSQL
                   │
                   ▼
              DJ Worker (AI + TTS)
                   │
                   ▼
            Liquidsoap ──► Icecast ──► Stream
```

**Audio flow**: Liquidsoap reads `/mnt/music` → track change hits API → DJ Worker generates commentary → TTS audio → queued back into Liquidsoap via telnet.

**MCP server**: port 8811, used by Pingos for `get_now_playing`, `skip_track`, `get_history`, `get_stream_status`, `get_dj_voices`, `set_dj_voice`.

---

## Configuration

Key `.env` settings:

```bash
DJ_PROVIDER=ollama                  # ollama or openai
OLLAMA_BASE_URL=http://<ip>:11434
DJ_VOICE_PROVIDER=chatterbox        # chatterbox, kokoro, openai_tts, xtts
DJ_COMMENTARY_INTERVAL=1            # 1 = after every song
POSTGRES_PASSWORD=...
JWT_SECRET=...
```

---

## TTS

### Chatterbox (primary)

External TTS at `192.168.1.170:8150`, accessed via `chatterbox-shim` proxy (port 18000). Kokoro is the fallback — circuit breaker trips after 5 consecutive failures (30s cooldown).

- **300-character limit** — DJ worker truncates at word boundary automatically
- Chatterbox must be on LAN IP; Docker can't reach Tailscale IPs

```bash
# Health
curl http://192.168.1.170:8150/health

# Test TTS
curl -X POST http://192.168.1.170:8150/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "voice": "default", "response_format": "wav"}' \
  -o speech.wav
```

### Kokoro (fallback)

Neural TTS, port 8091. Set `DJ_VOICE_PROVIDER=kokoro` to use directly.

### AI Commentary

Set in DJ Admin (`/raido/admin`). Uses Ollama by default — configure `OLLAMA_BASE_URL` and pick a model (`llama3.2:3b` recommended). Prompt template supports `{{song_title}}`, `{{artist}}`, `{{album}}`, `{{year}}`.

---

## Web UI Pages

| Path | Description |
|------|-------------|
| `/now-playing` | Live track with skip |
| `/media` | Library with search + metadata editing |
| `/media/tracks/:id` | Track permalink |
| `/raido/admin` | DJ settings, TTS config, voice selection |
| `/raido/enrich` | Bulk MusicBrainz enrichment |
| `/analytics` | Play history + stats |
| `/stations` | Station management |
| `/history` | Recent history with commentary |

---

## API Reference

```
GET  /api/v1/now                    Current track + progress
GET  /api/v1/now/history            Recent play history
WS   /ws                            Real-time WebSocket

GET   /api/v1/tracks                List/search tracks
PATCH /api/v1/tracks/{id}           Update metadata (writes ID3 tags)

GET  /api/v1/admin/settings         DJ/station settings
POST /api/v1/admin/settings         Update settings
GET  /api/v1/admin/voices           Available TTS voices
GET  /api/v1/admin/tts-status       TTS activity + pagination
```

---

## Development

```bash
make dev-setup      # Complete dev setup
make up-dev         # Start with live reload
make logs-api       # API logs
make logs-dj        # DJ worker logs
make logs-liquidsoap
make health         # Check all services
make shell-api      # Shell into API container
```

Dev URLs: Web `localhost:3000` · API `localhost:8001` · Stream `localhost:8000/raido.mp3`

---

## Monitoring

A lightweight monitor service checks API, Web, and Stream availability and sends **Pingos (Matrix)** notifications on failure.

```bash
cd monitoring && docker compose -f docker-compose.monitoring.yml up -d
```

See [monitoring/README.md](monitoring/README.md) for setup. Local health check: `make health`.

---

## Troubleshooting

**No audio**: check `make logs-liquidsoap` — verify music files in `/mnt/music`.

**DJ commentary silent**: check `make logs-dj` → verify TTS + Ollama in DJ Admin → press Skip to force an intro.

**Chatterbox not working**: `curl http://192.168.1.170:8150/health` — if unreachable, Kokoro fallback is active. Check `docker logs raido-chatterbox-shim-1`.

**Web not loading**: `make logs-proxy` → prod: `docker compose build web && make restart`.

For detailed recovery procedures see [RECOVERY.md](RECOVERY.md).

---

## TODO

- [ ] **MCP write tools** — `queue_track`, `update_dj_persona`, `inject_commentary` endpoints + MCP wiring
- [ ] **Raido → Pingos fast path** — replace built-in Pingos `check_raido` with full MCP server (port 8811 already running)
- [ ] **Auth** — most API endpoints are currently unprotected; JWT infrastructure exists in `services/api/app/core/security.py`
- [ ] **Lidarr auto-scan** — verify webhook reliably triggers artist folder scan after download completes
