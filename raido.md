# RAIDO #
# OVERVIEW #
#### Below are environment variables for the application raido. This file is on a system that will not rarely be connected to the internet so I want to make sure I can do development work without losing functionality. The entire 30k music library is not present on this sytem but some sample files are. It has environment varibles so do not commit it to git.

# Proxmox
## This is where I have many containers running including raido and ollama prod servers. Sometimes I will connect over Tailscale. Below are SSH credentials to the proxmox server that runs the prod servers
pct_raido=127
pct_ollama=227
host=192.168.1.193
ssh_username=root
ssh_password=BBVZoREAcChVxN9ePQLbJoDi8c389VHv

# Github
## I have the repo for raido hosted on Github. Always make sure you're committing to a branch that's not master
https://github.com/bhsuarez/raido

# Directories
## Music files location
### Local Development
music_files = ./music (subfolder in this directory)
- Place sample MP3, FLAC, OGG, or WAV files in ./music folder
- Currently empty - add files to test

### Production (Proxmox)
music_files = /mnt/music (30k track library)

# Development Setup Status
## This Mac system is configured for offline development
### Setup Complete
- Repository cloned from https://github.com/bhsuarez/raido
- `make setup` completed successfully (directories and .env configured)
- Docker Desktop required to run services

### Development Commands
```bash
# Start Docker Desktop first, then:
make up-dev          # Start development services with live reload
make health          # Check service health status
make logs            # View all service logs
make down            # Stop all services
```

### Services Architecture
- **API**: FastAPI backend (port 8001)
- **Web**: React frontend with Vite dev server (port 3000)
- **DJ Worker**: AI commentary generation and TTS processing
- **Liquidsoap**: Audio streaming engine
- **Icecast**: Streaming server (port 8000)
- **PostgreSQL**: Database
- **Chatterbox TTS**: External TTS service (192.168.1.112:8000) via chatterbox-shim proxy

### Important Notes
- This system has sample music files only (not full 30k library)
- Development mode enables hot reload for API and frontend
- raido.md contains credentials - DO NOT commit to git (already in .gitignore)

### Architecture Differences: Production vs Development
**Production (Proxmox):**
- Raido runs in container pct_raido=127 (192.168.1.193)
- Ollama runs in separate container pct_ollama=227 (192.168.1.204)
- Services connect over network

**Local Development (Mac):**
- Raido services run in Docker containers
- Ollama runs directly on Mac host (localhost:11434)
- Docker containers access host via `host.docker.internal:11434`
- Confirmed working: Ollama running with models (deepseek-r1, qwen2.5:32B, phi-3, mistral, llama2, llava)

### Current Status (Working)
✅ All services running successfully
- Frontend: http://localhost:3000 (via Caddy proxy)
- API: http://localhost:8001
- Stream: http://localhost:8000/stream/raido.mp3
- Database: PostgreSQL initialized with tables

### Fixes Applied
1. **Ollama connectivity**: Updated .env to use `host.docker.internal:11434`
2. **Music directory**: Added `./music` volume mount in docker-compose.override.yml
3. **Shared directory**: Added `./shared` volume mount for TTS cache and logs
4. **Proxy configuration**: Fixed Caddyfile.dev to proxy to `web-dev:3000` instead of `web:80`