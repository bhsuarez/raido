# 🎵 Raido Multi-Station Guide

This guide explains how to add and manage multiple radio stations in Raido.

## Table of Contents
- [Overview](#overview)
- [Quick Start: Adding a New Station](#quick-start-adding-a-new-station)
- [Station Configuration Reference](#station-configuration-reference)
- [Architecture](#architecture)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Overview

Raido supports running multiple independent radio stations, each with:
- ✅ Dedicated Liquidsoap instance (separate audio stream)
- ✅ Independent DJ worker (station-specific commentary)
- ✅ Separate frontend (optional custom UI)
- ✅ Station-specific settings (voice, provider, music filters)

**All configuration is managed through `stations.yml`** - no manual docker-compose editing required!

## Quick Start: Adding a New Station

### Step 1: Edit stations.yml

Add your station configuration to `stations.yml`:

```yaml
stations:
  # ... existing stations ...

  jazz:
    display_name: "Jazz Lounge 24/7"
    identifier: "jazz"
    description: "Smooth jazz all day and night"

    liquidsoap:
      config_file: "./infra/liquidsoap/jazz.liq"
      telnet_port: 1236
      http_port: null
      icecast_mount: "/jazz"

    dj_worker:
      enabled: true
      default_provider: "ollama"
      default_voice_provider: "kokoro"
      default_voice: "af_bella"
      commentary_interval: 2
      max_seconds: 20

    frontend:
      enabled: true
      port: 9002
      theme: "dark"

    music:
      path: "/mnt/music"
      filter:
        genre: ["Jazz", "Smooth Jazz", "Bebop"]
```

### Step 2: Create Liquidsoap Configuration

Create `infra/liquidsoap/jazz.liq`:

```liquidsoap
# Jazz Station - Smooth Jazz 24/7

# Settings
set("log.file", false)
set("log.stdout", true)
set("log.level", 3)

# Enable telnet server
set("server.telnet", true)
set("server.telnet.bind_addr", "0.0.0.0")
set("server.telnet.port", 1236)

# Music playlist (filtered by genre in your music library)
music = playlist(
  mode="randomize",
  reload_mode="watch",
  "/mnt/music"  # Filter handled by file scanner
)

# TTS commentary source
tts = request.queue(id="tts_queue")

# Mix music and commentary
radio = fallback(
  track_sensitive=false,
  [tts, music]
)

# Output to Icecast
output.icecast(
  %mp3(bitrate=128),
  host="icecast",
  port=8000,
  password="hackme",
  mount="/jazz",
  name="Jazz Lounge 24/7",
  description="Smooth jazz all day and night",
  genre="Jazz",
  url="https://yourstation.com",
  radio
)
```

### Step 3: Generate Docker Services

```bash
python3 scripts/generate-station-services.py
```

This creates `docker-compose.stations.yml` with all station services.

### Step 4: Sync Database

```bash
docker compose exec api python /app/../scripts/sync-stations-db.py
```

Or run from host:
```bash
python3 scripts/sync-stations-db.py
```

### Step 5: Start Services

```bash
# Start all services including new station
docker compose -f docker-compose.yml -f docker-compose.stations.yml up -d

# Or rebuild specific services
docker compose -f docker-compose.yml -f docker-compose.stations.yml build jazz-dj-worker
docker compose -f docker-compose.yml -f docker-compose.stations.yml up -d jazz-dj-worker jazz-liquidsoap
```

### Step 6: Verify

```bash
# Check services are running
docker compose ps | grep jazz

# Test API endpoint
curl http://localhost:8001/api/v1/now/?station=jazz | jq .

# Listen to stream
mpv http://localhost:8000/jazz
```

## Station Configuration Reference

### Required Fields

```yaml
identifier: "mystation"         # Unique ID (a-z, 0-9, -)
display_name: "My Station"      # Human-readable name
liquidsoap:
  config_file: "./infra/liquidsoap/mystation.liq"
  telnet_port: 1237             # Unique port for telnet
```

### Optional DJ Worker

```yaml
dj_worker:
  enabled: true                              # Enable DJ commentary
  default_provider: "ollama"                 # ollama, openai, templates, disabled
  default_voice_provider: "kokoro"           # kokoro, chatterbox, openai_tts
  default_voice: "am_onyx"                   # Voice identifier
  commentary_interval: 1                     # Commentary every N tracks
  max_seconds: 30                            # Max commentary length
  memory_limit: "1g"                         # Docker memory limit
  cpu_limit: "0.50"                          # Docker CPU limit
  prompt_template: |                         # Custom DJ prompt (optional)
    You're a jazz DJ introducing {{song_title}} by {{artist}}...
```

### Optional Frontend

```yaml
frontend:
  enabled: true          # Create web frontend
  port: 9002            # Port (null = main proxy route)
  theme: "dark"         # Theme name
  custom_branding: true # Custom branding enabled
```

### Music Filtering

```yaml
music:
  path: "/mnt/music"
  filter:                    # Optional filters
    genre: ["Jazz", "Blues"]
    tags: ["instrumental"]
    year_min: 1950
    year_max: 2000
```

**Note:** Filtering requires database metadata. Run music scanner first:
```bash
curl -X GET "http://localhost:8001/api/v1/metadata/scan_music_directory"
```

## Architecture

### Service Naming Convention

For station `mystation`:
- **Liquidsoap**: `mystation-liquidsoap`
- **DJ Worker**: `mystation-dj-worker`
- **Frontend**: `mystation-web` (or `web` for main station)

### Port Allocation

Each station needs unique ports:
- **Telnet**: 1234+ (Liquidsoap control)
- **Frontend**: 9000+ (if dedicated port)
- **Icecast mount**: Shared server, different mounts

| Station   | Telnet | Frontend | Icecast Mount |
|-----------|--------|----------|---------------|
| main      | 1234   | 80       | /stream       |
| christmas | 1235   | 9000     | /christmas    |
| jazz      | 1236   | 9002     | /jazz         |

### Database Integration

Each station gets:
- **Row in `stations` table**: Core metadata
- **Settings in `settings` table**: DJ configuration (filtered by `station` column)
- **Independent history**: Plays, commentary, artwork

### API Endpoints

All API endpoints support `?station=<identifier>`:

```bash
# Now playing for specific station
GET /api/v1/now/?station=jazz

# Next up for specific station
GET /api/v1/now/next?station=jazz

# History for specific station
GET /api/v1/now/history?station=jazz

# Settings for specific station
GET /api/v1/admin/settings?station=jazz
POST /api/v1/admin/settings?station=jazz
```

## Examples

### Example 1: Rock Station

```yaml
rock:
  display_name: "Rock Radio"
  identifier: "rock"
  description: "Classic and modern rock"

  liquidsoap:
    config_file: "./infra/liquidsoap/rock.liq"
    telnet_port: 1237
    http_port: null
    icecast_mount: "/rock"

  dj_worker:
    enabled: true
    default_provider: "ollama"
    default_voice_provider: "kokoro"
    default_voice: "am_michael"
    commentary_interval: 1
    max_seconds: 25
    prompt_template: |
      You're an energetic rock DJ. Introduce "{{song_title}}" by {{artist}}.
      Share a cool fact about the song or band. Keep it rockin'!

  frontend:
    enabled: true
    port: 9003
    theme: "dark"

  music:
    path: "/mnt/music"
    filter:
      genre: ["Rock", "Hard Rock", "Alternative Rock", "Classic Rock"]
```

### Example 2: Lo-Fi Study Station (No DJ)

```yaml
lofi:
  display_name: "Lo-Fi Study Beats"
  identifier: "lofi"
  description: "Chill beats to study/relax to"

  liquidsoap:
    config_file: "./infra/liquidsoap/lofi.liq"
    telnet_port: 1238
    http_port: null
    icecast_mount: "/lofi"

  dj_worker:
    enabled: false  # No commentary, just music

  frontend:
    enabled: true
    port: 9004
    theme: "dark"

  music:
    path: "/mnt/music"
    filter:
      genre: ["Lo-Fi", "Chillhop", "Instrumental Hip Hop"]
      tags: ["chill", "study"]
```

### Example 3: News & Talk Station

```yaml
news:
  display_name: "News & Talk Radio"
  identifier: "news"
  description: "24/7 news and discussion"

  liquidsoap:
    config_file: "./infra/liquidsoap/news.liq"
    telnet_port: 1239
    http_port: null
    icecast_mount: "/news"

  dj_worker:
    enabled: true
    default_provider: "openai"  # Use GPT for news commentary
    default_voice_provider: "openai_tts"
    default_voice: "onyx"
    commentary_interval: 1
    max_seconds: 45  # Longer segments for news

  frontend:
    enabled: false  # Share main frontend

  music:
    path: "/mnt/podcasts"  # Different content directory
```

## Troubleshooting

### Station Not Appearing

**Check service status:**
```bash
docker compose ps | grep mystation
```

**Regenerate services:**
```bash
python3 scripts/generate-station-services.py
docker compose -f docker-compose.yml -f docker-compose.stations.yml up -d
```

**Check database:**
```bash
docker compose exec db psql -U raido -d raido -c "SELECT * FROM stations WHERE identifier='mystation';"
```

### DJ Worker Not Generating Commentary

**Check logs:**
```bash
docker compose logs -f mystation-dj-worker
```

**Verify station name:**
```bash
docker compose exec mystation-dj-worker env | grep STATION_NAME
```

**Test API endpoint:**
```bash
curl "http://localhost:8001/api/v1/now/?station=mystation" | jq .
```

### Port Conflicts

Ensure each station has unique ports:
```bash
# Check for port conflicts
docker compose -f docker-compose.yml -f docker-compose.stations.yml config | grep "ports:" -A 1
```

### Liquidsoap Not Starting

**Check config syntax:**
```bash
# Validate liquidsoap config
docker run --rm -v $(pwd)/infra/liquidsoap:/config savonet/liquidsoap:v2.2.5 \
  liquidsoap --check /config/mystation.liq
```

**Check logs:**
```bash
docker compose logs mystation-liquidsoap
```

### Music Not Playing

**Verify music path:**
```bash
docker compose exec mystation-liquidsoap ls /mnt/music
```

**Check Liquidsoap telnet:**
```bash
echo "request.all" | telnet localhost 1237
```

## Advanced Topics

### Shared Music Library with Filters

All stations can share `/mnt/music` but filter by metadata:

1. **Scan library** to populate database
2. **Apply filters** in `stations.yml`
3. **Liquidsoap** uses filtered playlist

### Custom Frontend Theming

1. Copy `web/` to `web-mystation/`
2. Customize theme in `web-mystation/src/`
3. Build: `docker compose build mystation-web`

### Dynamic Station Creation

Create stations programmatically:

```python
import yaml

# Load config
with open('stations.yml') as f:
    config = yaml.safe_load(f)

# Add station
config['stations']['newstation'] = {...}

# Save
with open('stations.yml', 'w') as f:
    yaml.dump(config, f)

# Regenerate
os.system('python3 scripts/generate-station-services.py')
```

### Monitoring Multiple Stations

Use Prometheus + Grafana to monitor all stations:
- Track playback across stations
- Monitor DJ worker health
- Alert on stream failures

## Best Practices

1. **Port Planning**: Reserve port ranges (1234-1249 for telnet, 9000-9019 for frontends)
2. **Resource Limits**: Set appropriate CPU/memory limits per station
3. **Database Backups**: Backup before adding stations
4. **Gradual Rollout**: Test one station before scaling
5. **Documentation**: Document station purpose and configuration

## Getting Help

- **Logs**: `docker compose logs -f <service>`
- **Health Check**: `docker compose ps`
- **API Debug**: `curl http://localhost:8001/api/v1/now/?station=<id> | jq .`
- **Liquidsoap Console**: `telnet localhost <port>`

For more help, see [CLAUDE.md](CLAUDE.md) and [RECOVERY.md](RECOVERY.md).
