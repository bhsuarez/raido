# Raido Recovery Guide

## Quick Recovery Commands

### After System Crash or Restart

**Development Environment:**
```bash
# 1. Essential setup (creates required directories)
make setup

# 2. Start all services in development mode
make up-dev

# 3. Verify all services are running
make health
```

**Production Environment:**
```bash
# 1. Essential setup (creates required directories)
make setup

# 2. Start all services in production mode
make up

# 3. Run database migrations if needed
make migrate

# 4. Verify all services are running
make health
```

## Detailed Recovery Procedures

### 1. Development Environment Recovery

```bash
# Step 1: Stop any running containers (cleanup)
make down

# Step 2: Essential setup - CRITICAL STEP
make setup
# This creates required Docker volume directories that services need

# Step 3: Start development stack
make up-dev
# This starts: API, DJ Worker, Web (dev server), DB, Icecast, Liquidsoap, Kokoro TTS, Ollama

# Step 4: Wait for services to initialize (30-60 seconds)
sleep 60

# Step 5: Verify service health
make health

# Step 6: Check specific service logs if issues
make logs-api       # API backend
make logs-dj        # DJ Worker (TTS/AI commentary)
make logs-web       # Frontend development server

# Step 7: Initialize music library (if empty database)
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"
```

**Development URLs:**
- Frontend: http://localhost:3000 (with hot reload)
- API: http://localhost:8001
- Stream: http://localhost:8000/stream/raido.mp3

### 2. Production Environment Recovery

```bash
# Step 1: Stop any running containers (cleanup)
make down

# Step 2: Essential setup - CRITICAL STEP
make setup
# Creates required directories in Docker volumes

# Step 3: Build production containers (if updated)
make build

# Step 4: Start production stack
make up
# This starts: API, DJ Worker, Web (nginx), DB, Icecast, Liquidsoap, Kokoro TTS, Proxy (Caddy)

# Step 5: Run database migrations
make migrate

# Step 6: Wait for services to initialize (30-60 seconds)
sleep 60

# Step 7: Verify service health
make health

# Step 8: Check service logs if issues
make logs-api
make logs-dj
make logs-web

# Step 9: Initialize music library (if needed)
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"
```

**Production URLs:**
- Frontend: http://localhost (via Caddy proxy)
- API: http://localhost:8001
- Stream: http://localhost:8000/stream/raido.mp3

## Troubleshooting Common Issues

### Issue: Services Won't Start

**Symptoms:**
- Containers exit immediately
- "Directory not found" errors
- Database connection failures

**Solution:**
```bash
# Always run setup first - this is the #1 cause of startup failures
make setup
make up-dev  # or make up for production
```

### Issue: DJ Worker Not Running

**Symptoms:**
- No TTS commentary
- DJ Worker container missing from `docker compose ps`

**Solution:**
```bash
# Check if DJ Worker is in the container list
docker compose ps

# If missing, start it specifically
docker compose up -d dj-worker ollama

# Check logs for errors
make logs-dj
```

### Issue: TTS Not Working

**Symptoms:**
- No voice commentary between tracks
- "System protection active" in logs

**Quick Fix:**
```bash
# Restart DJ Worker with correct TTS configuration
docker compose restart dj-worker

# Start Kokoro TTS if not running
docker compose up -d kokoro-tts

# Verify TTS configuration
grep DJ_VOICE_PROVIDER .env
# Should be: DJ_VOICE_PROVIDER=kokoro
```

### Issue: No Analytics Data

**Symptoms:**
- Empty track history
- No play statistics

**Solution:**
```bash
# Check if music library is scanned
curl -X GET "http://localhost:8001/api/v1/now/history?limit=5"

# If empty, scan music library
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"

# Trigger a test track change
curl -X POST "http://localhost:8001/api/v1/liquidsoap/track_change" \
  -H "Content-Type: application/json" \
  -d '{"filename": "/music/test.mp3", "artist": "Test", "title": "Test Track"}'
```

## Service Dependencies

**Critical Services (must be running):**
- `db` (PostgreSQL) - Database
- `api` - Backend API
- `liquidsoap` - Audio streaming
- `icecast` - Stream server

**Optional Services:**
- `dj-worker` - AI commentary and TTS
- `kokoro-tts` - Text-to-speech engine
- `ollama` - Local LLM for commentary
- `web` or `web-dev` - Frontend interface
- `proxy` - Production reverse proxy

## Environment-Specific Notes

### Development Environment
- Uses `docker-compose.override.yml` for dev-specific settings
- Frontend runs on separate dev server (port 3000) with hot reload
- API runs with `--reload` flag for auto-restart on code changes
- Source code is mounted for live development

### Production Environment
- Uses optimized static builds
- All traffic goes through Caddy reverse proxy
- No source code mounting
- Containers use production-optimized images

## Quick Health Check

```bash
# Check all service status
docker compose ps

# Expected services in development:
# - raido-api-1
# - raido-db-1 
# - raido-dj-worker-1
# - raido-web-dev-1
# - raido-liquidsoap-1
# - raido-icecast-1
# - raido-kokoro-tts-1
# - raido-ollama-1

# Test API endpoint
curl http://localhost:8001/api/v1/now/

# Test stream
curl -I http://localhost:8000/stream/raido.mp3
```

## Emergency Contacts / Documentation

- Main Documentation: `CLAUDE.md`
- Docker Compose Config: `docker-compose.yml` + `docker-compose.override.yml`
- Environment Config: `.env`
- Service Logs: `make logs` or `docker compose logs [service]`