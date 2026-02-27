# Raido - AI Radio

A 24/7 AI-powered radio station with live DJ commentary, built with modern web technologies and containerized for easy deployment.

## Now Playing
<img width="600" height="800" alt="Image" src="https://github.com/user-attachments/assets/250aa1b2-3878-47c8-a64a-c8fdebae001a" />

## TTS Monitoring queue

<img width="600" height="800" alt="Image" src="https://github.com/user-attachments/assets/f6b62aec-d624-4708-a415-6789b78d70cc" />

## Raido Stations
<img width="600" height="800" alt="Image" src="https://github.com/user-attachments/assets/3c0da62f-1463-4ce9-a7b6-ee3fd794b264" />

## MusicBrainz Enrichment
<img width="600" height="800" alt="Image" src="https://github.com/user-attachments/assets/e625149e-7316-41cf-9abd-37479953307f" />

## Features

- **24/7 Music Streaming**: Continuous music playback from your local collection
- **AI DJ Commentary**: Dynamic commentary generated using Ollama (local) or OpenAI
  - Configurable prompt templates via DJ Admin interface
- **Multiple TTS Options**: Chatterbox TTS (primary), Kokoro TTS, OpenAI TTS, or XTTS
- **Modern Web Interface**: Responsive React frontend with real-time updates
- **Live Updates**: WebSocket integration for real-time track changes
- **Media Library**: Browse, search, and filter your music collection with track permalinks
- **Metadata Editing**: Edit track metadata inline with MusicBrainz lookup support
- **MusicBrainz Enrichment**: Bulk and per-track enrichment from MusicBrainz database
- **Admin Dashboard**: Configure DJ settings, monitor TTS activity, manage stations
- **Analytics**: Track play counts, history, and upcoming queue
- **Docker Ready**: Fully containerized with Docker Compose
- **Observability**: Structured logging, health endpoints, and Signal monitoring alerts

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
         │   (HTTPS)       │     │       │   (/mnt/music)  │
         └─────────────────┘     │       └─────────────────┘
```

### External TTS Services

```
DJ Worker ──► Chatterbox Shim (port 18000) ──► Chatterbox TTS (192.168.1.170:8150)
           └► Kokoro TTS (port 8091)                     (fallback when shim primary fails)
           └► OpenAI TTS (cloud)
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
   # AI commentary provider (ollama or openai)
   DJ_PROVIDER=ollama
   OPENAI_API_KEY=sk-your-openai-api-key-here  # Required if using openai

   # TTS provider (chatterbox, kokoro, openai_tts, or xtts)
   DJ_VOICE_PROVIDER=chatterbox

   # Database password
   POSTGRES_PASSWORD=your_secure_password
   ```

4. **Add music**:
   ```bash
   mkdir -p music
   # Copy your music files to ./music directory
   ```

5. **Build and start Raido (production)**:
   ```bash
   # Option 1: Full production setup (recommended)
   make production-setup

   # Option 2: Manual production build and start
   make build    # Build all services with production optimizations
   make up       # Start all services in production mode
   make migrate  # Run database migrations

   # Option 3: Selective service deployment
   docker compose build web api dj-worker
   docker compose up -d proxy api web icecast liquidsoap dj-worker
   make migrate
   ```

6. **Scan your music library**:
   ```bash
   curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"
   # Then extract embedded artwork
   curl -X POST "http://localhost:8001/api/v1/artwork/batch_extract?limit=100"
   ```

### Access Points (production)

- **Web UI**: http://localhost
- **DJ Admin**: http://localhost/raido/admin
- **API (via proxy)**: http://localhost/api/v1
- **Stream**: http://localhost:8000/raido.mp3
- **pgAdmin**: http://localhost:5050

## Web Interface

### Pages

| Path | Description |
|------|-------------|
| `/now-playing` | Live now-playing display with progress and skip |
| `/media` | Music library with search, filters, and metadata editing |
| `/media/tracks/:id` | Track permalink — direct link to a track's metadata panel |
| `/raido/admin` | DJ Admin — TTS settings, prompt templates, voice selection |
| `/raido/enrich` | Bulk MusicBrainz metadata enrichment |
| `/analytics` | Play history and track statistics |
| `/stations` | Station management |
| `/history` | Recent play history with commentary |

### Track Permalinks & Metadata Editing

Every track has a permanent URL at `/media/tracks/:id`. You can:

- Click any track in the Media Library to open its metadata panel and update the URL
- Click the pencil icon next to the current track title in Now Playing to jump directly to its edit panel
- Share or bookmark `/media/tracks/123` to return directly to a specific track
- Edit title, artist, album, year, and genre inline and save to both the database and audio file tags
- Search MusicBrainz for matching releases and apply artwork, metadata, and MBIDs with one click
- Paste a MusicBrainz release URL or UUID for a manual lookup

## AI Commentary

### Ollama (Local LLM)

```bash
# Point DJ Worker to a remote Ollama server
OLLAMA_BASE_URL=http://<remote-ip>:11434

# Restart the worker after changes
docker compose restart dj-worker

# Verify connectivity
curl http://<remote-ip>:11434/api/tags
```

**Recommended models:**
- Lightweight: `llama3.2:1b` (fast on CPU)
- Balanced: `llama3.2:3b` or `llama3.1:8b`

### Prompt Template

- Open DJ Admin at `/raido/admin`
- Set "Commentary Provider" to `Ollama` or `OpenAI`
- Edit the Prompt Template textarea — supports Jinja variables:
  - `{{song_title}}`, `{{artist}}`, `{{album}}`, `{{year}}`
- Click "Save Settings" — applies immediately to the DJ worker

## TTS Configuration

### Chatterbox TTS (Primary)

Chatterbox is an external TTS service accessed via the `chatterbox-shim` proxy:

```bash
# In .env
DJ_VOICE_PROVIDER=chatterbox
CHATTERBOX_BASE_URL=http://chatterbox-shim:18000

# Shim upstream (LAN IP required — Docker can't reach Tailscale IPs)
CH_SHIM_UPSTREAM=http://192.168.1.170:8150,http://kokoro-tts:8880
```

The `chatterbox-shim` service (port 18000) proxies requests to Chatterbox at `192.168.1.170:8150`, falling back to Kokoro if Chatterbox is unreachable. Chatterbox is always tried first; the circuit breaker trips after 5 consecutive failures (30s cooldown) and routes to Kokoro during that window.

**Notes:**
- Chatterbox has a **300-character text limit** — the DJ worker truncates at word boundary automatically
- The Voice & TTS Settings UI shows Chatterbox as an option only when the shim reports it healthy
- Chatterbox uses `POST /v1/audio/speech` (OpenAI-compatible); the legacy `GET /tts` endpoint is not used

**Chatterbox API (direct):**
```bash
# Health check
curl http://192.168.1.170:8150/health

# OpenAI-compatible TTS
curl -X POST "http://192.168.1.170:8150/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "voice": "default", "response_format": "wav"}' \
  -o speech.wav

# Via shim (as DJ worker uses it)
curl -X POST "http://localhost:18000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "voice": "default"}' \
  -o speech.wav
```

### Kokoro TTS

High-quality neural TTS, runs locally on port 8091:

```bash
DJ_VOICE_PROVIDER=kokoro
KOKORO_BASE_URL=http://kokoro-tts:8880
KOKORO_VOICE=am_onyx   # am_onyx, af_bella, etc.
KOKORO_SPEED=1.0
```

```bash
cd kokoro-tts
./start-cpu.sh   # CPU inference
./start-gpu.sh   # GPU inference (requires NVIDIA GPU)
```

List available voices:
```bash
curl http://localhost/api/v1/admin/voices | jq .voices
```

### OpenAI TTS

```bash
DJ_VOICE_PROVIDER=openai_tts
OPENAI_API_KEY=sk-your-key-here
```

### XTTS (Experimental)

Docker Compose defines an `xtts-server` service using `synesthesiam/opentts:en` on port 5500:

```bash
DJ_VOICE_PROVIDER=xtts
XTTS_BASE_URL=http://xtts-server:5500
```

Switch via DJ Admin: `/raido/admin` → Voice Provider → XTTS.

## Development

### Quick Start

```bash
# Complete development environment setup
make dev-setup
# Runs: setup → build → up-dev → migrate
```

### Manual Setup

```bash
make setup      # Create .env, directories
make build      # Build all containers
make up-dev     # Start with live reload (docker-compose.override.yml)
```

### Development URLs

- **Web UI**: http://localhost:3000 (Caddy → Vite with HMR)
- **API Direct**: http://localhost:8001 (health at `/health`)
- **Stream**: http://localhost:8000/raido.mp3
- **Database Admin**: http://localhost:8081 (Adminer)

### Build Commands

```bash
# Build all services
make build

# Build individual services
docker compose build api         # FastAPI backend
docker compose build dj-worker   # AI commentary worker
docker compose build web         # React frontend (production nginx)

# Rebuild after frontend changes
docker compose build web && make restart

# Verbose build output
docker compose build --progress=plain api
```

### Workflow

```bash
make up-dev          # Start dev stack
make restart-dev     # Restart api, web-dev, proxy
make restart-web     # Restart web-dev only
make restart-api     # Restart api only
make down-dev        # Stop dev stack
make logs-web        # Tail web-dev logs (Vite)
make logs-api        # Tail API logs
make status          # Show container status
```

### Production Deployment

```bash
make setup          # Initial setup and .env configuration
make build          # Build production containers
make up             # Start all services
make migrate        # Run database migrations
make health         # Verify deployment
make status         # Container status
```

**Production optimizations:**
- Static React assets minified and bundled
- Multi-stage Docker builds for smaller images
- Non-root users in all containers
- HTTPS termination via Caddy proxy
- Memory and CPU limits per service

## Configuration

### DJ Settings

```bash
# AI Provider (ollama or openai)
DJ_PROVIDER=ollama
OPENAI_API_KEY=your-key-here

# TTS Provider (chatterbox, kokoro, openai_tts, or xtts)
DJ_VOICE_PROVIDER=chatterbox

# Commentary frequency (1 = after every song)
DJ_COMMENTARY_INTERVAL=1

# Max commentary length in seconds
DJ_MAX_SECONDS=30

# Station identity
STATION_NAME="Raido"
DJ_TONE=energetic
```

### Stream Settings

```bash
ICECAST_BITRATE=128
STREAM_FORMAT=mp3
CROSSFADE_DURATION=2.0
```

### Security

```bash
POSTGRES_PASSWORD=very-secure-password
JWT_SECRET=very-long-random-secret-key
CORS_ORIGINS=https://yourdomain.com
```

## Music Library

**Supported formats:** MP3, FLAC, OGG Vorbis, WAV

### File Organization

```
music/
├── Artist1/
│   ├── Album1/
│   │   ├── 01 - Song1.mp3
│   │   └── 02 - Song2.mp3
│   └── Album2/
├── Artist2/
└── Various/
```

### Metadata

Raido reads ID3 tags for title, artist, album, year, genre, embedded artwork, and duration. After scanning, use the Media Library at `/media` to edit metadata per-track or the MusicBrainz enrichment tool at `/raido/enrich` for bulk updates.

## Monitoring & Alerts

A lightweight monitor service checks API, Web, and Stream availability and sends **Signal** notifications on failure.

```bash
# Start monitoring
cd monitoring && docker compose -f docker-compose.monitoring.yml up -d

# Configure Signal notifications
cp monitoring/.env.monitoring.example monitoring/.env.monitoring
# Edit .env.monitoring with your Signal phone numbers
```

See [monitoring/README.md](monitoring/README.md) for full setup instructions.

Local health check:
```bash
make health   # Checks API (8001), Web (3000), Stream (8000)
```

## API Reference

### Now Playing

```
GET  /api/v1/now                   Current playing track + progress
GET  /api/v1/now/history           Recent play history
GET  /api/v1/now/next              Upcoming tracks
WS   /ws                           Real-time WebSocket updates
```

### Tracks

```
GET   /api/v1/tracks               List/search tracks (search, genre, artist, sort, page)
GET   /api/v1/tracks/facets        Distinct genres, artists, albums for filters
GET   /api/v1/tracks/{id}          Get single track
PATCH /api/v1/tracks/{id}          Update track metadata (writes ID3 tags to file)
GET   /api/v1/tracks/{id}/musicbrainz               Search MusicBrainz
GET   /api/v1/tracks/{id}/musicbrainz/release/{mbid} Lookup specific release
```

### Admin

```
GET  /api/v1/admin/settings        Get DJ/station settings
POST /api/v1/admin/settings        Update settings
GET  /api/v1/admin/stats           System statistics
GET  /api/v1/admin/voices          List available TTS voices
GET  /api/v1/admin/tts-status      TTS activity window and pagination
```

Full interactive docs at `/docs` (Swagger UI).

## Troubleshooting

**No audio playing:**
```bash
make logs-liquidsoap
# Check for music files in ./music
# Verify file permissions
```

**DJ commentary not working:**
```bash
make logs-dj
# Verify Provider/Voice Provider in DJ Admin (/raido/admin)
# Check Chatterbox shim: curl http://localhost:18000/health
# Check Kokoro: curl http://localhost:8091/health
# Check Ollama: curl http://<ollama-host>:11434/api/tags
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
# Dev: ensure web-dev is up and proxy uses Caddyfile.dev
# Prod: docker compose build web && make restart
```

**PostgreSQL container error:**
```bash
docker compose down -v
docker image rm postgres:16 || true
docker system prune -af
docker compose pull db
docker compose up -d db
```

See [RECOVERY.md](RECOVERY.md) for detailed recovery procedures and [instructions.md](instructions.md) for a step-by-step runbook.

## Screenshots

- Home: `docs/screenshots/home.png`
- DJ Admin: `docs/screenshots/dj-admin.png`

## Build Troubleshooting

```bash
# Clean rebuild after issues
make clean
docker system prune -af
make build

# Clear build cache
docker builder prune

# Verbose build output
docker compose build --progress=plain api
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run linters: `make lint`
5. Format code: `make format`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **Liquidsoap**: Audio streaming engine
- **Icecast**: Streaming server
- **FastAPI**: Modern Python web framework
- **React**: Frontend library
- **Ollama**: Local LLM inference
- **MusicBrainz**: Music metadata database
- **Docker**: Containerization platform
