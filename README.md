# 🏴‍☠️ Raido - AI Pirate Radio

A 24/7 AI-powered radio station with live DJ commentary, built with modern web technologies and containerized for easy deployment.

## Features

- **🎵 24/7 Music Streaming**: Continuous music playback from your collection
- **🤖 AI DJ Commentary**: Dynamic commentary generated using OpenAI or Ollama
- **🎙️ Multiple TTS Options**: Kokoro TTS, OpenAI TTS, XTTS, or basic speech synthesis
- **📱 Modern Web Interface**: Responsive React frontend with real-time updates
- **🔄 Live Updates**: WebSocket integration for real-time track changes
- **📊 Admin Dashboard**: Configure DJ settings, monitor stats, manage users
- **🎨 Pirate Theme**: Custom pirate-themed design with dark mode
- **🐳 Docker Ready**: Fully containerized with Docker Compose
- **📈 Observability**: Structured logging and health monitoring

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web     │    │   FastAPI       │    │   DJ Worker     │
│   Frontend      │◄──►│   Backend       │◄──►│   (AI/TTS)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        ▼                        │
         │              ┌─────────────────┐                │
         └─────────────►│   PostgreSQL    │                │
                        │   Database      │                │
                        └─────────────────┘                │
                                 ▲                         │
         ┌─────────────────┐     │       ┌─────────────────┐
         │   Icecast       │◄────┼──────►│   Liquidsoap    │
         │   Streaming     │     │       │   Audio Engine  │
         └─────────────────┘     │       └─────────────────┘
                  ▲              │                ▲
                  │              │                │
         ┌─────────────────┐     │       ┌─────────────────┐
         │   Caddy Proxy   │     │       │   Music Files   │
         │   (HTTPS)       │     │       │   (/music)      │
         └─────────────────┘     │       └─────────────────┘
                                 │
                        ┌─────────────────┐
                        │   Redis Cache   │
                        │   (Optional)    │
                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker with Docker Compose v2
- At least 2GB RAM
- Music files (MP3, FLAC, OGG, WAV)

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd raido
   ```

2. **Initial setup**:
   ```bash
   make setup
   ```

3. **Configure environment**:
   Edit `.env` file with your settings:
   ```bash
   # Required for AI commentary
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Database password
   POSTGRES_PASSWORD=your_secure_password
   
   # Other settings...
   ```

4. **Add music**:
   ```bash
   mkdir -p music
   # Copy your music files to ./music directory
   ```

5. **Start Raido (production)**:
   ```bash
   # Build optimized web and start the core stack
   docker compose build web
   docker compose up -d proxy api web icecast liquidsoap dj-worker
   ```

6. **Run database migrations**:
   ```bash
   make migrate
   ```

### Access Points (production)

- **Web UI**: http://localhost
- **DJ Admin**: http://localhost/tts
- **API (via proxy)**: http://localhost/api/v1
- **Stream**: http://localhost:8000/raido.mp3
- **pgAdmin**: http://localhost:5050

## Development

### Dev Run (Vite + hot reload)

```bash
# Start dev stack (Caddy→Vite @ :3000, API @ :8001)
make up-dev

# Useful
make restart-dev     # restart api, web-dev, proxy
make restart-web     # restart web-dev only
make restart-api     # restart api only
make logs-web        # tail web-dev logs (Vite)
make logs-api        # tail api logs
make logs-proxy      # tail proxy logs
```

Dev URLs:
- Web UI: http://localhost:3000 (Caddy → Vite)
- API: http://localhost:8001 (health at /health)
- Stream: http://localhost:8000/raido.mp3

Notes:
- The dev web service (`web-dev`) runs Node + Vite with your code mounted and auto‑reloads on save.
- The API runs Uvicorn with `--reload` and picks up Python changes.
- For production web rebuilds, run `docker compose build web && docker compose up -d web`.

### Monitoring & Alerts

- A lightweight `monitor` service runs in the stack and periodically checks API, Web, and Stream availability.
- To enable Slack alerts on failures, set `ALERT_SLACK_WEBHOOK` in your `.env` file.
- You can also run `make health` locally; it checks host ports (API on `8001`, Web on `3000`, Stream on `8000`).

## Configuration

### DJ Settings

Configure AI commentary in `.env`:

```bash
# AI Provider (openai or ollama)
DJ_PROVIDER=openai
OPENAI_API_KEY=your-key-here

# TTS Provider (kokoro, openai_tts, liquidsoap, or xtts)
DJ_VOICE_PROVIDER=kokoro

# Commentary frequency (1 = after every song)
DJ_COMMENTARY_INTERVAL=1

# Max commentary length in seconds
DJ_MAX_SECONDS=30

# DJ personality
DJ_TONE=energetic
STATION_NAME="Raido Pirate Radio"
```

### Kokoro TTS Settings

For high-quality neural TTS using Kokoro:

```bash
# TTS Provider
DJ_VOICE_PROVIDER=kokoro

# Kokoro TTS Configuration
KOKORO_BASE_URL=http://kokoro-tts:8880
KOKORO_VOICE=am_onyx  # Available voices: am_onyx, af_bella, etc.
KOKORO_SPEED=1.0
```

**Starting Kokoro TTS:**
```bash
cd kokoro-tts
./start-cpu.sh  # For CPU inference
# or
./start-gpu.sh  # For GPU inference (requires NVIDIA GPU)
```

List all voices through the API:
```bash
curl http://localhost/api/v1/admin/voices | jq .voices
```

### XTTS (Experimental)

You can try XTTS via an OpenTTS container to compare synthesis speed/quality.

1) Docker Compose already defines an `xtts-server` service using `synesthesiam/opentts:en`.
   - It listens on `5500` inside the Docker network.
   - Set `XTTS_BASE_URL=http://xtts-server:5500` in your environment (see `.env.example`).
   - Choose a voice that OpenTTS provides for XTTS (e.g., `coqui-xtts-high`).

2) Switch the voice provider in the DJ Admin UI:
   - Navigate to `/tts` in the Web UI.
   - Set “Voice Provider” to `XTTS`.
   - Optionally adjust voice name under settings if needed.

3) Observe generation time in the TTS dashboard:
   - Recent activity lists per-item `TTS` timing.
   - The “Avg TTS Time” card shows average over the window.

Notes:
- The worker attempts two API styles: POST `${XTTS_BASE_URL}/tts` and GET `${XTTS_BASE_URL}/api/tts` (OpenTTS).
- You can tail logs with `make logs-xtts`.

### Stream Settings

```bash
# Stream quality
ICECAST_BITRATE=128
STREAM_FORMAT=mp3

# Crossfade between tracks
CROSSFADE_DURATION=2.0
```

### Security

For production deployment:

```bash
# Use strong passwords
POSTGRES_PASSWORD=very-secure-password
JWT_SECRET=very-long-random-secret-key

# Set allowed origins
CORS_ORIGINS=https://yourdomain.com

# Configure HTTPS in Caddy
```

## Music Library

Raido supports:
- **MP3** (recommended)
- **FLAC** (high quality)
- **OGG Vorbis**
- **WAV**

### File Organization

```
music/
├── Artist1/
│   ├── Album1/
│   │   ├── 01 - Song1.mp3
│   │   ├── 02 - Song2.mp3
│   └── Album2/
├── Artist2/
└── Various/
```

### Metadata

Raido reads ID3 tags for:
- Title, Artist, Album
- Year, Genre
- Embedded artwork
- Duration

## API Documentation

### Core Endpoints

- `GET /api/v1/now` - Current playing track
- `GET /api/v1/now/history` - Play history
- `GET /api/v1/now/next` - Upcoming tracks
- `WS /ws` - Real-time updates

### Admin Endpoints

- `GET /api/v1/admin/settings` - Get settings
- `POST /api/v1/admin/settings` - Update settings
- `GET /api/v1/admin/stats` - System statistics
- `GET /api/v1/admin/voices` - List Kokoro voices (proxy)
- `GET /api/v1/admin/tts-status?window_hours=24&limit=100` - TTS activity window + pagination

See `/docs` endpoint for full API documentation.

## Troubleshooting

### Common Issues

**No audio playing:**
```bash
make logs-liquidsoap
# Check for music files in ./music directory
# Verify file permissions
```

**DJ commentary not working:**
```bash
make logs-dj
# Verify Provider/Voice Provider in DJ Admin (/tts)
# Ensure Kokoro is running (http://localhost:8091/health)
# Check Ollama model exists and base URL is correct
# Press Skip to force an intro
```

**Database connection issues:**
```bash
make logs-api
# Check POSTGRES_PASSWORD in .env
# Ensure database container is running
```

**Web interface not loading:**
```bash
make logs-proxy
# Dev: ensure web-dev is up (make logs-web) and proxy uses Caddyfile.dev
# Prod: rebuild web (docker compose build web) and restart
```

If PostgreSQL shows a manifest/`ContainerConfig` error:
```bash
docker compose down -v
docker image rm postgres:16 || true
docker system prune -af
docker compose pull db
docker compose up -d db
```

See also: `instructions.md` for a step-by-step runbook.

## Screenshots

- Home: `docs/screenshots/home.png`
- DJ Admin: `docs/screenshots/dj-admin.png`

### Debugging

Enable debug logging:
```bash
# In .env
APP_DEBUG=true
LOG_LEVEL=debug
```

Check service status:
```bash
make status
make health
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `make test`
5. Format code: `make format`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Liquidsoap**: Audio streaming engine
- **Icecast**: Streaming server
- **FastAPI**: Modern Python web framework
- **React**: Frontend library
- **OpenAI**: AI commentary generation
- **Docker**: Containerization platform

---

**🏴‍☠️ Ahoy! Set sail with your own AI pirate radio station!**

For support, issues, or feature requests, please visit our GitHub repository.
