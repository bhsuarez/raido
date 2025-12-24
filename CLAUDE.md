# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 System Crash Recovery

**Quick Recovery Commands:**
- Development: `make setup && make up-dev && make health`
- Production: `make setup && make up && make migrate && make health`

For detailed recovery procedures, troubleshooting, and emergency fixes, see **[RECOVERY.md](RECOVERY.md)**.

## Essential Commands

### Development Setup
```bash
make dev-setup          # Complete development environment setup
make setup               # Basic setup (copy .env, create directories) - REQUIRED BEFORE make up
```

**IMPORTANT**: Always run `make setup` before starting services. This creates required directories in Docker volumes that the API needs to start properly.

### Service Management
```bash
make up                  # Start all services in production mode
make up-dev              # Start services in development mode with live reload
make down                # Stop all services
make restart             # Restart all services
```

### Database Operations
```bash
make migrate             # Run database migrations
make migrate-create name=migration_name  # Create new migration
make shell-db            # Open PostgreSQL shell
make backup-db           # Create database backup
```

### Music Library Management
```bash
# Scan music library to populate database (run after initial setup)
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"

# Extract artwork from audio files that have embedded artwork
curl -X POST "http://localhost:8001/api/v1/artwork/batch_extract?limit=100"
```

**Note**: After initial setup, run the music scan to populate the database with track metadata. This enables proper artwork display and track information.

### Development & Debugging
```bash
make logs                # Show all service logs
make logs-api            # API service logs
make logs-dj             # DJ worker logs
make logs-liquidsoap     # Audio streaming engine logs
make logs-web            # Frontend logs
make shell-api           # Shell into API container
make shell-dj            # Shell into DJ worker container
make health              # Check service health status
```

### Monitoring & Alerts
```bash
# Start monitoring with Signal notifications
cd monitoring && docker compose -f docker-compose.monitoring.yml up -d

# Configure Signal notifications (first time setup)
cp monitoring/.env.monitoring.example monitoring/.env.monitoring
# Edit .env.monitoring with your Signal phone numbers

# View monitoring logs
docker compose -f monitoring/docker-compose.monitoring.yml logs -f raido-monitor
```

**Important**: Signal API runs on port 8082 (changed from 8080 to avoid Liquidsoap conflicts).
**See [monitoring/README.md](monitoring/README.md) for complete setup instructions.**

### Code Quality
```bash
make lint                # Run linters (ruff for Python, eslint for TypeScript)
make format              # Format code (ruff format, eslint --fix)
```

### Build & Container Management
```bash
make build               # Build all services (API, DJ Worker, Web)
docker compose build     # Alternative direct build command
docker compose build api # Build specific service
docker compose build web # Build web frontend only
docker compose build dj-worker # Build DJ worker only
make clean               # Clean up containers, volumes, and images
make clean-all           # Nuclear cleanup - remove everything
```

### Frontend Development
```bash
cd web && npm run dev    # Start frontend dev server with hot reload
cd web && npm run build  # Build production frontend
cd web && npm run lint   # Lint TypeScript/React code
make build web           # Build web container with optimized React build
```

### Production Deployment
```bash
make production-setup    # Complete production setup
make build               # Build all production containers
make up                  # Start in production mode
docker compose up -d proxy api web icecast liquidsoap dj-worker # Selective start
```

## Architecture Overview

Raido is a containerized AI-powered radio station with the following core services:

**Constraints:**  
- Runs in Docker + Docker Compose v2.  
- Privacy-first (minimal exposure of secrets).  
- HTTPS enforced end-to-end.

### Core Services
- **API (`services/api/`)** - FastAPI backend handling REST APIs, WebSocket connections, and database operations
- **DJ Worker (`services/dj-worker/`)** - Background service for AI commentary generation and TTS processing
- **Web (`web/`)** - React frontend with TypeScript, Vite build system, and real-time WebSocket updates
- **Liquidsoap** - Audio streaming engine that mixes music and TTS commentary
- **Icecast** - Streaming server broadcasting the final audio stream
- **PostgreSQL** - Primary database for track history, settings, and user data

### External Integration Services
- **Chatterbox TTS** - External TTS service (192.168.1.170:8000) accessed via chatterbox-shim proxy
- **Chatterbox Shim** - Local proxy service (port 18000) providing OpenAI-compatible API for Chatterbox TTS
- **Kokoro TTS** - Neural text-to-speech service (runs on port 8091, internal 8880)
- **Ollama** - Local LLM service for AI commentary generation (enabled)
- **OpenAI TTS** - Cloud-based TTS service (alternative option)
- **Caddy** - Reverse proxy handling HTTPS and routing

### Audio Processing Flow
1. **Liquidsoap** reads music files from `/mnt/music` and streams to Icecast
2. **Track changes** trigger API calls to `/api/v1/liquidsoap/track_change`
3. **DJ Worker** generates AI commentary and converts to audio via TTS
4. **TTS audio** is queued in Liquidsoap via telnet interface (port 1234)
5. **Mixed stream** (music + commentary) broadcasts via Icecast

## Project Structure

### Backend Services
- `services/api/app/` - FastAPI application with routes, models, database
- `services/dj-worker/app/` - DJ worker with AI clients (OpenAI, Ollama, Kokoro)
- `services/dj-worker/app/services/` - TTS, commentary generation, API clients
- `services/dj-worker/app/worker/` - Main DJ worker loop

### Frontend
- `web/src/components/` - React components (NowPlaying, AdminPanel, etc.)
- `web/src/store/` - Zustand state management
- `web/src/hooks/` - Custom React hooks
- `web/src/utils/` - Utility functions and API clients

### Infrastructure
- `infra/liquidsoap/radio.liq` - Liquidsoap audio streaming configuration
- `infra/Caddyfile` - Reverse proxy configuration
- `docker-compose.yml` - Service orchestration
- `.env` - Environment configuration

## Key Technical Details

### Database Migrations
- Uses Alembic for SQL migrations
- Migration files in `services/api/app/alembic/versions/`
- Always run `make migrate` after database schema changes

### AI Commentary System
- **Providers**: OpenAI GPT models, local Ollama models, or static templates
- **TTS Options**: Chatterbox TTS (via shim proxy), Kokoro TTS (neural), OpenAI TTS, or XTTS
- **Flow**: Track change → API → DJ Worker → AI generation → TTS → Audio queue
- **Configuration**: DJ settings via `.env` (currently: DJ_PROVIDER=ollama, DJ_VOICE_PROVIDER=chatterbox)
- **Admin UI**: DJ settings configurable via web interface with prompt templates and voice selection
- **TTS Proxy**: `chatterbox-shim` service provides OpenAI-compatible API for external Chatterbox TTS

### Audio Processing
- **Music Directory**: `/mnt/music` (supports MP3, FLAC, OGG, WAV)
- **Metadata**: Uses Mutagen library for ID3 tag reading
- **Streaming**: Liquidsoap manages audio mixing and Icecast streaming
- **TTS Queue**: Interactive request queue with 10s timeout
- **TTS Cache**: Generated audio files cached in `/shared/tts` with automatic cleanup

### WebSocket Real-time Updates
- **Endpoint**: `/ws` for live track changes and system status
- **Frontend**: React hooks for WebSocket connection management
- **Data**: Now playing, track history, system health updates

### Development Environment
- **Hot Reload**: Frontend via Vite, backend via file mounting
- **Logs**: Centralized logging with structured output
- **Health Checks**: All services include health check endpoints with automated monitoring
- **Database Admin**: pgAdmin4 available on port 5050
- **Resource Management**: Services configured with memory limits and CPU constraints
- **TTS Cleanup**: Automated cleanup service for cached TTS files

### Security Considerations
- **JWT Authentication** for API endpoints
- **CORS Configuration** via CORS_ORIGINS environment variable  
- **Secrets Management** via .env file (never commit real secrets)
- **Container Security** with non-root users in all services

## Important File Paths
- **Music Library**: `/mnt/music` (mounted from host)
- **Shared Storage**: `/shared` for TTS cache and logs
- **Database**: PostgreSQL data persisted in Docker volume
- **TTS Cache**: `/shared/tts` for generated audio files
- **Configuration**: `.env` file for all service configuration

## Build and Deployment Guide

### Container Build Process

**Individual Service Builds:**
```bash
# API Service (FastAPI backend)
docker compose build api
# Built from: ./services/api/Dockerfile
# Base image: Python with FastAPI dependencies

# DJ Worker (AI commentary and TTS)  
docker compose build dj-worker
# Built from: ./services/dj-worker/Dockerfile
# Base image: Python with AI/ML dependencies

# Web Frontend (React/TypeScript)
docker compose build web
# Built from: ./web/Dockerfile
# Multi-stage build: Node.js build → nginx serve
```

**Production Build Flow:**
```bash
# 1. Build all containers with production optimizations
make build

# 2. Start production stack with optimized web build
make up

# 3. Alternative selective deployment
docker compose up -d proxy api web icecast liquidsoap dj-worker
```

**Development Build Flow:**
```bash  
# 1. Build development environment
make dev-setup

# 2. Start with live reload (uses docker-compose.override.yml)
make up-dev

# 3. Frontend development with Vite hot reload
# Uses web-dev service with mounted source code
```

### Environment Configurations

**Development Environment:**
- Uses `docker-compose.override.yml` for dev-specific overrides
- API runs with `--reload` flag for Python hot reload
- Web runs via `web-dev` service with Vite dev server
- Source code mounted for live development
- Exposed ports: API (8001), Web (3000), Stream (8000)

**Production Environment:**  
- Uses base `docker-compose.yml` configuration
- Web built into static files served by nginx
- All services behind Caddy reverse proxy
- HTTPS termination and routing handled by Caddy
- Access via port 80/443 through proxy

### Build Optimization

**Web Frontend Build:**
```bash
# Development - Vite dev server with HMR
make up-dev  # Uses web-dev service

# Production - Optimized static build
make build   # Creates production React build
make up      # Serves via nginx
```

**Container Caching:**
- Multi-stage Dockerfiles for optimal layer caching
- Package managers (npm, pip) run before source code copy
- Production images exclude development dependencies
- Build context optimized with .dockerignore

### Deployment Strategies

**Local Development:**
```bash
make dev-setup    # Complete dev environment  
make restart-dev  # Restart dev services only
make logs-web     # Monitor frontend dev server
make logs-api     # Monitor backend with reload
```

**Production Deployment:**  
```bash
make production-setup  # Production setup wizard
make build            # Build all production images
make up               # Start production services
make migrate          # Run database migrations
make health           # Verify deployment health
```

**Container Management:**
```bash
make status        # Show container status
make monitoring    # Resource usage stats  
make clean-caches  # Clean build caches safely
make update        # Update and rebuild all services
```

## Common Development Tasks

### Adding New API Endpoints
1. Add route in `services/api/app/routes/`
2. Update models in `services/api/app/models/` if needed
3. Run database migration if schema changes required
4. Update frontend API client in `web/src/utils/`
5. **Rebuild API container**: `docker compose build api`

### Modifying DJ Behavior
- **Commentary Logic**: `services/dj-worker/app/services/commentary_generator.py`
- **TTS Integration**: `services/dj-worker/app/services/tts_service.py` 
- **AI Clients**: `services/dj-worker/app/services/{openai,ollama,kokoro}_client.py`
- **Rebuild DJ Worker**: `docker compose build dj-worker`

### Frontend Development
- **Components**: Add to `web/src/components/`
- **State**: Use Zustand store in `web/src/store/`
- **Styling**: Tailwind CSS classes, custom CSS in `web/src/index.css`
- **Real-time**: WebSocket hooks in `web/src/hooks/`
- **Development**: Use `make up-dev` for live reload
- **Production Build**: `docker compose build web && make restart`

### Testing Changes
- **Health Checks**: `make health` to verify all services
- **Service Logs**: Use `make logs-{service}` to debug issues
- **Audio Stream**: Check http://localhost:8000/stream/raido.mp3
- **Frontend**:
  - Development: http://localhost:3000 (live reload)
  - Production: http://localhost (via proxy)

## Recent Fixes (September 2025)

### TTS Audio Playback Issues - RESOLVED
- **Problem**: TTS files not playing in browser, generating 105-byte error files instead of audio
- **Root Cause**:
  1. API client bug in `dj_worker.py:258` - incorrect attribute `session` instead of `client`
  2. External Chatterbox TTS service connectivity via chatterbox-shim proxy
- **Fix Applied**:
  1. Fixed API client HTTP client reference in DJ worker
  2. Configured chatterbox-shim to proxy requests to external Chatterbox service (192.168.1.170:8000)
  3. Updated environment configuration for proper TTS service integration
- **Verification**: Manual TTS tests now generate proper 50KB+ MP3 files accessible via web interface

### Voice Cloning Interface Removal - RESOLVED
- **Problem**: Voice cloning page still accessible and visible in navigation
- **Root Cause**: React routes and navigation components not properly updated
- **Fix Applied**:
  1. Removed `/voices` route from `web/src/App.tsx`
  2. Removed Voice Cloning navigation link from `web/src/components/Layout.tsx`
  3. Rebuilt frontend with asset cache invalidation (new hash: `index-CMHznLHM.js`)
- **Verification**: `/voices` now shows 404 page, navigation no longer displays voice cloning option

### System Status
- **TTS Provider**: Chatterbox TTS (external) via chatterbox-shim proxy
- **AI Provider**: Ollama (local LLM service)
- **Frontend**: Production build with voice cloning removed
- **Audio Pipeline**: Fully functional with automated commentary generation
- Chatterbox Backend Server (Port 8000)

  GET Endpoints:

  - GET /tts - Text-to-speech generation
    - Parameters:
        - text (required): Text to synthesize
      - audio_prompt_path (optional): Path to audio file for voice cloning
    - Returns: WAV audio file
  - GET /health - Health check
    - Returns: {"status": "ok"}

  POST Endpoints:

  - POST /v1/audio/speech - OpenAI-compatible TTS
    - Body: {"input": "text", "voice": "voice_name"}
    - Supports voice mapping (e.g., "brian")
    - Returns: WAV audio file

  Frontend Upload Server (Port 8080)

  GET Endpoints:

  - GET /api/status - Server status
  - GET /api/voices - List available voices

  POST Endpoints:

  - POST /api/upload-voice - Upload WAV files for voice cloning
  - POST /api/download-voice - Download audio from URLs using yt-dlp

  Usage Examples:

  # Basic TTS
  curl "http://192.168.1.170:8000/tts?text=Hello%20world" -o output.wav

  # Voice cloning TTS
  curl "http://192.168.1.170:8000/tts?text=Hello&audio_prompt_path=/path/to/voice.wav" -o cloned.wav

  # OpenAI-compatible
  curl -X POST "http://192.168.1.170:8000/v1/audio/speech" \
    -H "Content-Type: application/json" \
    -d '{"input": "Hello world", "voice": "brian"}' \
    -o speech.wav

  All endpoints support CORS and return audio as WAV files.