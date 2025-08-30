# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Development Setup
```bash
make dev-setup          # Complete development environment setup
make setup               # Basic setup (copy .env, create directories)
```

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

### Code Quality
```bash
make lint                # Run linters (ruff for Python, eslint for TypeScript)
make format              # Format code (ruff format, eslint --fix)
```

### Frontend Development
```bash
cd web && npm run dev    # Start frontend dev server with hot reload
cd web && npm run build  # Build production frontend
cd web && npm run lint   # Lint TypeScript/React code
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
- **Kokoro TTS** - Neural text-to-speech service (runs on port 8091, internal 8880)
- **Ollama** - Local LLM service for AI commentary generation
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
- **Providers**: OpenAI GPT models or local Ollama models
- **TTS Options**: Kokoro TTS (neural), OpenAI TTS, or basic synthesis
- **Flow**: Track change → API → DJ Worker → AI generation → TTS → Audio queue
- **Configuration**: DJ settings via `.env` (DJ_PROVIDER, DJ_VOICE_PROVIDER, etc.)

### Audio Processing
- **Music Directory**: `/mnt/music` (supports MP3, FLAC, OGG, WAV)
- **Metadata**: Uses Mutagen library for ID3 tag reading
- **Streaming**: Liquidsoap manages audio mixing and Icecast streaming
- **TTS Queue**: Interactive request queue with 10s timeout

### WebSocket Real-time Updates
- **Endpoint**: `/ws` for live track changes and system status
- **Frontend**: React hooks for WebSocket connection management
- **Data**: Now playing, track history, system health updates

### Development Environment
- **Hot Reload**: Frontend via Vite, backend via file mounting
- **Logs**: Centralized logging with structured output
- **Health Checks**: All services include health check endpoints
- **Database Admin**: pgAdmin4 available on port 5050

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

## Common Development Tasks

### Adding New API Endpoints
1. Add route in `services/api/app/routes/`
2. Update models in `services/api/app/models/` if needed
3. Run database migration if schema changes required
4. Update frontend API client in `web/src/utils/`

### Modifying DJ Behavior
- **Commentary Logic**: `services/dj-worker/app/services/commentary_generator.py`
- **TTS Integration**: `services/dj-worker/app/services/tts_service.py` 
- **AI Clients**: `services/dj-worker/app/services/{openai,ollama,kokoro}_client.py`

### Frontend Development
- **Components**: Add to `web/src/components/`
- **State**: Use Zustand store in `web/src/store/`
- **Styling**: Tailwind CSS classes, custom CSS in `web/src/index.css`
- **Real-time**: WebSocket hooks in `web/src/hooks/`

### Testing Changes
- **Health Checks**: `make health` to verify all services
- **Service Logs**: Use `make logs-{service}` to debug issues
- **Audio Stream**: Check http://localhost:8000/stream/raido.mp3
- **Frontend**: http://localhost:3000 with hot reload in dev mode