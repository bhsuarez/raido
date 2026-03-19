# Jazz Station Design

**Date:** 2026-03-18
**Status:** Approved

## Overview

Add a jazz radio station to Raido following the exact multi-station pattern already used by `christmas`, `recent`, and `newreleases`. No new infrastructure or code changes required — the entire feature is delivered through config files and Docker Compose service entries.

## Components

### 1. `stations.yml` entry

> **Note:** `stations.yml` already contains a commented-out jazz template at line 113 that assigns `telnet_port: 1236`. That port is owned by `recent`. Do not use that stub — add the block defined below instead.

New `jazz` block:

```yaml
jazz:
  display_name: "Jazz Lounge"
  identifier: "jazz"
  description: "Smooth jazz 24/7 — late-night vibes, live commentary"

  liquidsoap:
    config_file: "./infra/liquidsoap/jazz.liq"
    telnet_port: 1238
    http_port: null
    icecast_mount: "/jazz.mp3"

  dj_worker:
    enabled: true
    default_provider: "ollama"
    default_voice_provider: "kokoro"
    default_voice: "am_onyx"
    commentary_interval: 1
    max_seconds: 30
    memory_limit: "1g"
    cpu_limit: "0.50"
    prompt_template: |
      You're a smooth late-night jazz radio DJ introducing the NEXT track coming up.
      Create a brief 15-20 second intro for "{{song_title}}" by {{artist}} from the album {{album}} ({{year}}).
      Share ONE interesting fact — the recording session, the label, a notable collaborator, or the era it defined.
      Keep it mellow, unhurried, and knowledgeable. No hype, just cool.

  frontend:
    enabled: true
    port: null
    theme: "dark"
    custom_branding: false

  music:
    path: "/mnt/music"
    filter:
      genre: ["Jazz", "Smooth Jazz", "Bebop", "Cool Jazz", "Jazz Fusion"]
```

Port 1238 is the next available telnet port (1234=main, 1235=christmas, 1236=recent, 1237=newreleases).

### 2. `infra/liquidsoap/jazz.liq`

Modeled on `radio.liq` with one addition: a `skip_non_jazz` function. Unlike `skip_christmas` (which checks filename/title/album for a keyword), `skip_non_jazz` checks the `genre` ID3 metadata field — if it doesn't contain "jazz" (case-insensitive), the track is skipped. Genre tags are the reliable signal for a broad music category like jazz; filename/title heuristics would produce too many false negatives.

Key elements:
- Telnet on port 1238
- TTS queue id: `"tts_jazz"`
- Music source: `/mnt/music` (all music, filtered by genre skip)
- Station identifier in track_change payload: `"jazz"`
- Icecast mount: `/jazz`
- Name: `"Jazz Lounge"`

### 3. `docker-compose.yml` additions

Two new services, identical in structure to existing station services:

**`jazz-liquidsoap`:**
- Image: `savonet/liquidsoap:v2.2.5`
- Volumes: `/mnt/music` (read-only), `jazz.liq`, `shared`
- Port: `1238:1238`
- Depends on: `icecast`

**`jazz-dj-worker`:**
- Build: `./services/dj-worker`
- Environment: `STATION_NAME=jazz`, `LIQUIDSOAP_HOST=jazz-liquidsoap`, `LIQUIDSOAP_PORT=1238`
- Resource limits: `mem_limit: 1g`, `cpus: 0.50`
- Depends on: `api` (healthy)

## Data Flow

```
/mnt/music (all tracks)
  → jazz.liq skip_non_jazz filter (genre ID3 tag check)
  → jazz Liquidsoap source
  → track_change_handler → POST /api/v1/liquidsoap/track_change?station=jazz
  → jazz-dj-worker polls → Ollama generates commentary → Kokoro TTS → MP3
  → telnet inject into jazz Liquidsoap (port 1238)
  → TTS queue plays before next track
  → Icecast /jazz.mp3 mount
```

## Out of Scope

- No new API endpoints (genre filter is Liquidsoap-side, not API-side)
- No frontend theme changes (uses existing dark theme)
- No new Icecast configuration (ICECAST_MAX_SOURCES=10 already set, currently 4 stations in use)
- No DB schema changes
