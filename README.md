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

5. **Build and start Raido (production)**:
   ```bash
   # Option 1: Full production setup (recommended)
   make production-setup
   
   # Option 2: Manual production build and start
   make build  # Build all services with production optimizations
   make up     # Start all services in production mode
   make migrate # Run database migrations
   
   # Option 3: Selective service deployment
   docker compose build web api dj-worker  # Build core services
   docker compose up -d proxy api web icecast liquidsoap dj-worker
   make migrate
   ```

### Access Points (production)

- **Web UI**: http://localhost
- **DJ Admin**: http://localhost/tts
- **API (via proxy)**: http://localhost/api/v1
- **Stream**: http://localhost:8000/raido.mp3
- **pgAdmin**: http://localhost:5050

## Development

### Development Setup & Build Process

**Quick Development Start:**
```bash
# Complete development environment setup
make dev-setup
# This runs: setup → build → up-dev → migrate
```

**Manual Development Setup:**
```bash
# 1. Initial setup
make setup  # Create .env, directories

# 2. Build all development containers
make build  # Builds api, dj-worker, web services

# 3. Start development stack with live reload
make up-dev  # Uses docker-compose.override.yml
```

### Development Build Commands

**Container Builds:**
```bash
# Build all services
make build
docker compose build

# Build individual services
docker compose build api        # FastAPI backend
docker compose build dj-worker  # AI commentary worker  
docker compose build web        # React frontend (production)

# Development web service (live reload)
# Built automatically when using make up-dev
```

**Development vs Production Builds:**
```bash
# Development: Live reload with source mounting
make up-dev
# Uses web-dev service with Vite dev server
# Source code mounted for instant updates

# Production: Optimized static build  
make build && make up
# Creates production React build served by nginx
```

### Development Workflow

**Dev Stack Management:**
```bash
# Start dev stack (Caddy→Vite @ :3000, API @ :8001)
make up-dev

# Service management
make restart-dev     # restart api, web-dev, proxy
make restart-web     # restart web-dev only
make restart-api     # restart api only
make down-dev        # stop dev stack

# Monitoring
make logs-web        # tail web-dev logs (Vite)
make logs-api        # tail api logs
make logs-proxy      # tail proxy logs
make status          # show container status
```

**Development URLs:**
- **Web UI**: http://localhost:3000 (Caddy → Vite with HMR)  
- **API Direct**: http://localhost:8001 (health at /health)
- **Stream**: http://localhost:8000/raido.mp3
- **Database Admin**: http://localhost:8081 (Adminer)

### Build Architecture

**Development Environment:**
- **web-dev**: Node.js container running Vite dev server
- **API**: Python FastAPI with `--reload` flag
- **Source Mounting**: Code changes trigger automatic rebuilds
- **Hot Module Replacement**: Instant frontend updates
- **Override Configuration**: Uses `docker-compose.override.yml`

**Production Environment:**  
- **web**: Multi-stage build (Node.js build → nginx serve)
- **Optimized Assets**: Minified, bundled, cached
- **Reverse Proxy**: All traffic through Caddy
- **SSL Termination**: HTTPS handled by proxy layer

### Rebuilding After Changes

**Frontend Changes:**
```bash
# Development (automatic)
# Changes to web/ trigger Vite HMR automatically

# Production rebuild  
docker compose build web
make restart  # or: docker compose up -d web
```

**Backend Changes:**
```bash
# Development (automatic)  
# Python changes trigger uvicorn reload automatically

# Production rebuild
docker compose build api        # rebuild API
docker compose build dj-worker # rebuild DJ worker
make restart                   # restart services
```

**Environment Changes:**
```bash
# After .env changes
make restart        # restart all services
make restart-dev    # restart dev services only
```

### Monitoring & Alerts

- A lightweight `monitor` service runs in the stack and periodically checks API, Web, and Stream availability.
- To enable Slack alerts on failures, set `ALERT_SLACK_WEBHOOK` in your `.env` file.
- You can also run `make health` locally; it checks host ports (API on `8001`, Web on `3000`, Stream on `8000`).

## Build & Container Reference

### Service Build Details

**API Service (`services/api/`):**
```dockerfile
# Built from: services/api/Dockerfile  
# Base: python:3.11-slim
# Features: FastAPI, Alembic, PostgreSQL drivers
# Optimization: Multi-stage build, dependency caching
```

**DJ Worker (`services/dj-worker/`):**
```dockerfile  
# Built from: services/dj-worker/Dockerfile
# Base: python:3.11-slim  
# Features: OpenAI, Ollama clients, TTS integrations
# Optimization: AI/ML dependencies, model caching
```

**Web Frontend (`web/`):**
```dockerfile
# Built from: web/Dockerfile
# Stage 1: node:18 (build React app)
# Stage 2: nginx:alpine (serve static files)
# Features: Vite build, TypeScript, Tailwind CSS
# Optimization: Multi-stage, static asset serving
```

### Build Commands Reference

**Complete Build Commands:**
```bash
# Full stack build
make build                          # Build all services
docker compose build               # Alternative full build
docker compose build --no-cache    # Clean rebuild

# Production optimized builds  
make production-setup              # Complete production setup
docker compose build --pull       # Rebuild with latest base images

# Development builds
make dev-setup                     # Complete dev environment
make up-dev                       # Start with development overrides
```

**Individual Service Builds:**
```bash
# Backend services
docker compose build api          # FastAPI backend
docker compose build dj-worker    # AI commentary worker

# Frontend builds  
docker compose build web          # Production React build (nginx)
# Note: web-dev service uses mounted source, no build needed

# Infrastructure
docker compose pull kokoro-tts    # Neural TTS service
docker compose pull ollama        # LLM service  
```

**Build Troubleshooting:**
```bash
# Clean rebuild after issues
make clean                        # Remove containers and volumes
docker system prune -af           # Remove all unused containers
make build                        # Fresh rebuild

# Check build context and caches
docker compose build --progress=plain api  # Verbose build output
docker builder prune                       # Clear build cache
```

### Production Deployment Guide

**Full Production Setup:**
```bash
# 1. Initial setup and configuration
make setup
# Edit .env with production values (passwords, API keys, domains)

# 2. Build production containers  
make build

# 3. Deploy services
make up      # or: docker compose up -d

# 4. Initialize database
make migrate

# 5. Verify deployment
make health
make status
```

**Production Build Optimizations:**
- **Static Assets**: React app built and minified
- **Multi-stage Builds**: Smaller final images  
- **Dependency Caching**: Faster rebuilds
- **Security**: Non-root users in containers
- **SSL**: HTTPS termination via Caddy proxy
- **Resource Limits**: Memory and CPU constraints

**Scaling Considerations:**
```bash
# Resource monitoring
make monitoring               # Container resource usage
docker stats                 # Real-time container stats

# Service scaling (if needed)  
docker compose up -d --scale dj-worker=2  # Scale DJ workers
```

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
