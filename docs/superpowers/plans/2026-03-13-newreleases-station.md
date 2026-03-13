# New Releases Station Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "New Releases" radio station that plays tracks released in approximately the last 6 months, based on the `year` field in the Track model.

**Architecture:** Since tracks only store release `year` (integer, not a full date), the filter uses `year >= current_year - 1` as a 6-month approximation. The API writes `/shared/newreleases.m3u` hourly — identical pattern to the existing "recent" station which generates `/shared/recent.m3u`. A new Liquidsoap container reads that file and streams to Icecast at `/newreleases.mp3`.

**Tech Stack:** Python/FastAPI (playlist generation), Liquidsoap 2.2.5 (audio engine), Docker Compose (service orchestration)

---

## Files

| Action | File | What changes |
|--------|------|-------------|
| Modify | `services/api/app/main.py` | Add `_write_newreleases_playlist()` coroutine, launch it in `lifespan()` |
| Create | `infra/liquidsoap/newreleases.liq` | Liquidsoap config for the new station (port 1237, mount `/newreleases.mp3`) |
| Modify | `docker-compose.yml` | Add `newreleases-liquidsoap` and `newreleases-dj-worker` services |
| Modify | `services/api/app/api/v1/endpoints/now_playing.py` | Add `"newreleases"` entry to `STATION_LIQUIDSOAP_CONFIG` |
| Modify | `stations.yml` | Document new station (used for human reference / future tooling) |

---

## Task 1: Add playlist generator to main.py

**Files:**
- Modify: `services/api/app/main.py`

The `recent` station generates `/shared/recent.m3u` using `Track.created_at`. The new station generates `/shared/newreleases.m3u` using `Track.year`. Since `year` is an integer, filter `year >= current_year - 1` (e.g., in March 2026 this gives 2025+2026 tracks).

- [ ] **Step 1: Add `_write_newreleases_playlist()` to main.py after `_write_recent_playlist()`**

```python
async def _write_newreleases_playlist():
    """Write /shared/newreleases.m3u with tracks released in approximately the last 6 months.

    Uses Track.year >= current_year - 1 as an approximation since full release
    dates are not stored. Runs once on startup then refreshes hourly.
    """
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.tracks import Track

    while True:
        try:
            current_year = datetime.now(timezone.utc).year
            cutoff_year = current_year - 1
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Track.file_path)
                    .where(Track.year >= cutoff_year)
                    .where(~Track.file_path.like("liquidsoap://%"))
                    .order_by(Track.year.desc())
                )
                paths = [row[0] for row in result.fetchall()]

            content = "#EXTM3U\n" + "\n".join(paths) + "\n"
            with open("/shared/newreleases.m3u", "w") as f:
                f.write(content)
            logger.info("Wrote newreleases.m3u", track_count=len(paths))
        except Exception as e:
            logger.warning("Failed to write newreleases.m3u", error=str(e))

        await asyncio.sleep(3600)
```

- [ ] **Step 2: Launch the task in the `lifespan()` function**

Find where `_write_recent_playlist` is started in `lifespan()` and add the new one alongside it:

```python
asyncio.create_task(_write_newreleases_playlist())
```

- [ ] **Step 3: Verify the file looks correct**

```bash
grep -n "newreleases" services/api/app/main.py
```

Expected: 2 matches — the function definition and the `create_task` call.

---

## Task 2: Create newreleases.liq

**Files:**
- Create: `infra/liquidsoap/newreleases.liq`

Copy `recent.liq` exactly, then change 4 things: telnet port (1237), tts queue id, Icecast mount, and station name in the API payload.

- [ ] **Step 1: Create `infra/liquidsoap/newreleases.liq`**

```liquidsoap
#!/usr/bin/liquidsoap

# ----- Liquidsoap 2.2.x config for Raido New Releases -----
# Plays tracks released in approximately the last 6 months (year >= current_year - 1).
# The API writes /shared/newreleases.m3u hourly.
# If the playlist is empty/unavailable, the sine fallback keeps the stream alive.

settings.decoder.priorities.ffmpeg := 10
settings.decoder.priorities.mad    := 1

settings.init.allow_root := true
settings.log.level       := 4  # warn

# Telnet control (different port from main/christmas/recent to avoid conflicts)
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := 1237

# ---------- Sources ----------
tts_q = request.queue(id="tts_newreleases", timeout=30.0, interactive=true)

# New releases playlist — the API writes and refreshes this file hourly.
newreleases_music = playlist(
  mode="random",
  reload=300,
  reload_mode="watch",
  "/shared/newreleases.m3u"
)

# Helpers
def meta_get(m, k, d)
  if list.mem(k, list.map(fst, m)) then list.assoc(k, m) else d end
end

# Global variable to track last processed track (to avoid duplicates)
last_processed_track = ref("")

# Ensure sane metadata defaults
def rm_key(m, k)  list.filter(fun (kv) -> fst(kv) != k, m) end
def put_default(m, k, v)
  has = list.mem(k, list.map(fst, m))
  cur = if has then list.assoc(k, m) else "" end
  if (not has) or cur == "" then
    m2 = rm_key(m, k)
    list.append(m2, [(k, v)])
  else m end
end

def update_metadata(m)
  m = put_default(m, "title",  "Unknown")
  m = put_default(m, "artist", "Unknown Artist")
  m
end

# ---------- Chain / processing ----------
# Normalize metadata
music = metadata.map(update_metadata, newreleases_music)

# Wrap with insert_metadata so we can inject per-track StreamUrl (for artwork in players like Triode)
music_inj = insert_metadata(music)

# Combined callback: handles commentary generation and per-track logging
def track_change_handler(m)
  artist = meta_get(m, "artist", "Unknown artist")
  title  = meta_get(m, "title",  "Unknown title")
  album  = meta_get(m, "album",  "")

  track_key = artist ^ "|" ^ title

  if last_processed_track() != track_key then
    last_processed_track := track_key

    log("🆕 Now playing: " ^ title ^ " by " ^ artist)

    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '","station":"newreleases"}'
    url = "http://api:8000/api/v1/liquidsoap/track_change"

    def make_api_call()
      response = http.post(url, data=payload, headers=[("Content-Type", "application/json")])
      log("✅ API call response: " ^ response)
      # Extract artwork_url and inject as StreamUrl for players like Triode
      abs_matches = string.extract(pattern='"artwork_url":"(https?://[^"]+)"', response)
      abs_url = list.assoc(default="", 1, abs_matches)
      rel_matches = string.extract(pattern='"artwork_url":"(/[^"]+)"', response)
      rel_url = list.assoc(default="", 1, rel_matches)
      artwork_url = if abs_url != "" then abs_url
        elsif rel_url != "" then "http://192.168.1.41" ^ rel_url
        else "" end
      if artwork_url != "" then
        music_inj.insert_metadata([("url", artwork_url)])
        log("🎨 Set StreamUrl to: " ^ artwork_url)
      end
    end

    thread.run(make_api_call)
  end
end

# Attach the combined callback to the music source
music = source.on_metadata(music_inj, track_change_handler)

# Sine backup for emergency fallback
sine_src = sine()

# TTS gets priority when available, then falls back to music
primary = fallback(track_sensitive=true, [tts_q, music])

primary = source.on_track(primary, fun (m) -> log("🆕 Track starting: " ^ meta_get(m, "artist", "Unknown") ^ " - " ^ meta_get(m, "title", "Unknown")))
radio   = fallback(track_sensitive=false, [primary, sine_src])

# ---------- Output ----------
output.icecast(
  %mp3(id3v2=true),
  host="icecast",
  port=8000,
  user="source",
  password="hackme",
  mount="/newreleases.mp3",
  name="Raido New Releases",
  url="https://raido.local",
  genre="New Releases",
  description="Tracks released in approximately the last 6 months",
  radio
)

log("🆕 Raido New Releases streaming started!")
```

- [ ] **Step 2: Verify file was created**

```bash
wc -l infra/liquidsoap/newreleases.liq
```

Expected: ~75 lines.

---

## Task 3: Update docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

Add two services after `recent-dj-worker` (lines 173-192): `newreleases-liquidsoap` and `newreleases-dj-worker`.

- [ ] **Step 1: Add `newreleases-liquidsoap` service after the `recent-liquidsoap` block**

Insert after the `recent-liquidsoap` service (after line 64):

```yaml
  newreleases-liquidsoap:
    image: savonet/liquidsoap:v2.2.5
    restart: unless-stopped
    depends_on: [icecast]
    volumes:
      - /mnt/music:/mnt/music:ro
      - ./infra/liquidsoap/newreleases.liq:/newreleases.liq:ro
      - shared:/shared
    command: ["liquidsoap","/newreleases.liq"]
    ports: ["1237:1237"]
```

- [ ] **Step 2: Add `newreleases-dj-worker` service after the `recent-dj-worker` block**

Insert after the `recent-dj-worker` service (after line 192):

```yaml
  newreleases-dj-worker:
    build: ./services/dj-worker
    restart: unless-stopped
    env_file: .env
    depends_on:
      api:
        condition: service_healthy
    volumes: [shared:/shared]
    environment:
      - STATION_NAME=newreleases
      - LIQUIDSOAP_HOST=newreleases-liquidsoap
      - LIQUIDSOAP_PORT=1237
    healthcheck:
      test: ["CMD", "curl", "-f", "http://api:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: "1g"
    cpus: "0.50"
```

- [ ] **Step 3: Verify the YAML is valid**

```bash
cd /root/claude/raido-src && docker compose config --quiet && echo "YAML OK"
```

Expected: `YAML OK` (no errors).

---

## Task 4: Update now_playing.py

**Files:**
- Modify: `services/api/app/api/v1/endpoints/now_playing.py:17-21`

Add `"newreleases"` to `STATION_LIQUIDSOAP_CONFIG`.

- [ ] **Step 1: Add newreleases to STATION_LIQUIDSOAP_CONFIG**

Change:
```python
STATION_LIQUIDSOAP_CONFIG = {
    "main": {"host": "liquidsoap", "port": 1234},
    "christmas": {"host": "christmas-liquidsoap", "port": 1235},
    "recent": {"host": "recent-liquidsoap", "port": 1236},
}
```

To:
```python
STATION_LIQUIDSOAP_CONFIG = {
    "main": {"host": "liquidsoap", "port": 1234},
    "christmas": {"host": "christmas-liquidsoap", "port": 1235},
    "recent": {"host": "recent-liquidsoap", "port": 1236},
    "newreleases": {"host": "newreleases-liquidsoap", "port": 1237},
}
```

- [ ] **Step 2: Verify**

```bash
grep -A 6 "STATION_LIQUIDSOAP_CONFIG" services/api/app/api/v1/endpoints/now_playing.py
```

Expected: 5 entries including `newreleases`.

---

## Task 5: Update stations.yml

**Files:**
- Modify: `stations.yml`

Add the new station entry before the `# Example: Add more stations` comment.

- [ ] **Step 1: Add `newreleases` station to stations.yml**

Add after the `christmas` block (before line 79):

```yaml
  # New Releases station - recently released music
  newreleases:
    display_name: "New Releases"
    identifier: "newreleases"
    description: "Tracks released in approximately the last 6 months"

    liquidsoap:
      config_file: "./infra/liquidsoap/newreleases.liq"
      telnet_port: 1237
      http_port: null
      icecast_mount: "/newreleases.mp3"

    dj_worker:
      enabled: true
      default_provider: "ollama"
      default_voice_provider: "kokoro"
      default_voice: "am_onyx"
      commentary_interval: 1
      max_seconds: 30
      memory_limit: "1g"
      cpu_limit: "0.50"

    frontend:
      enabled: false
      port: null
      theme: "dark"
      custom_branding: false

    music:
      path: "/mnt/music"
      filter:
        year_min: current_year - 1  # approximation for last 6 months
```

---

## Task 6: Commit, push, and deploy

- [ ] **Step 1: Commit all changes**

```bash
cd /root/claude/raido-src
git add infra/liquidsoap/newreleases.liq \
        docker-compose.yml \
        services/api/app/main.py \
        services/api/app/api/v1/endpoints/now_playing.py \
        stations.yml \
        docs/superpowers/plans/2026-03-13-newreleases-station.md
git commit -m "feat: add New Releases station (tracks from last ~6 months by year)"
```

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Deploy to PCT 127**

```bash
pct exec 127 -- bash -c "cd /opt/raido && git pull raido main"
pct exec 127 -- bash -c "cd /opt/raido && docker compose build api"
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d"
```

- [ ] **Step 4: Verify new containers started**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose ps newreleases-liquidsoap newreleases-dj-worker"
```

Expected: both containers show `Up`.

- [ ] **Step 5: Verify the stream is live**

```bash
curl -I http://192.168.1.41:8000/newreleases.mp3
```

Expected: `HTTP/1.0 200 OK` with `Content-Type: audio/mpeg`.

- [ ] **Step 6: Verify the playlist was generated**

```bash
pct exec 127 -- bash -c "docker exec raido-api-1 wc -l /shared/newreleases.m3u"
```

Expected: at least 2 lines (header + tracks). If 1 line (just `#EXTM3U`), the library has no tracks with `year >= 2025` — check track metadata with `docker exec raido-api-1 python -c "from app.core.database import *; ..."`.
