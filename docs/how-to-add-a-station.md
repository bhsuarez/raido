# How to Add a New Radio Station to Raido

> **This is the ground-truth guide.** Based on the actual jazz station implementation (2026-03-18).
> Ignore `STATIONS.md` — it references non-existent scripts and has wrong port numbers.

---

## Overview

Each station requires exactly **3 file changes** and no code:

| File | Action | Purpose |
|------|--------|---------|
| `infra/liquidsoap/{name}.liq` | Create | Audio stream config, genre filter, TTS queue, Icecast output |
| `stations.yml` | Modify | Add station block (DJ persona, voice, prompt) |
| `docker-compose.yml` | Modify | Add two services: `{name}-liquidsoap` and `{name}-dj-worker` |

---

## Step 1: Assign a Telnet Port

Each station needs a **unique telnet port**. Current allocations:

| Station | Telnet Port | Icecast Mount |
|---------|-------------|---------------|
| main | 1234 | `/stream` (actually `/raido.mp3` in output) |
| christmas | 1235 | `/christmas.mp3` |
| recent | 1236 | `/recent.mp3` |
| newreleases | 1237 | `/newreleases.mp3` |
| jazz | 1238 | `/jazz.mp3` |
| **next new** | **1239** | `/{name}.mp3` |

---

## Step 2: Create `infra/liquidsoap/{name}.liq`

Copy the jazz station config and adapt it. Key things to customize:
- Telnet port (line: `settings.server.telnet.port`)
- TTS queue id: `tts_{name}` (must be unique across all stations)
- Station identifier in API payload: `\"station\":\"{name}\"`
- Icecast mount: `/{name}.mp3`
- Playlist source (see Genre Filtering section below)
- Log emoji/station name strings

### Genre filtering: use a pre-generated playlist file

**Do NOT use `source.on_track` + `skip()` for genre filtering.** It seems like it should work but doesn't — the skip loop rapid-fires through 99%+ non-matching tracks, exhausts Liquidsoap's request queue, and the station falls back to the sine beep.

**The correct approach for genre-filtered stations:**
1. Generate a text file of matching file paths from the database
2. Point Liquidsoap at that file with `playlist("/shared/{name}_tracks.txt")`
3. Set up a cron job on PCT 127 to regenerate the file every 30 min

```bash
# Generate the initial playlist (run on Proxmox host):
pct exec 127 -- bash << 'EOF'
cd /opt/raido && docker compose exec -T db psql -U raido -d raido -t -c \
  "SELECT file_path FROM tracks WHERE genre = '{Genre}' ORDER BY artist, album;" \
  | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' \
  > /var/lib/docker/volumes/raido_shared/_data/{name}_tracks.txt
wc -l /var/lib/docker/volumes/raido_shared/_data/{name}_tracks.txt
EOF

# Install cron job to refresh it (run on Proxmox host):
cat << 'SCRIPT' > /tmp/update-{name}-playlist.sh
#!/bin/bash
cd /opt/raido
PLAYLIST=/var/lib/docker/volumes/raido_shared/_data/{name}_tracks.txt
docker compose exec -T db psql -U raido -d raido -t -c \
  "SELECT file_path FROM tracks WHERE genre = '{Genre}' ORDER BY artist, album;" \
  | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' > "${PLAYLIST}.tmp"
COUNT=$(wc -l < "${PLAYLIST}.tmp")
[ "$COUNT" -gt 10 ] && mv "${PLAYLIST}.tmp" "$PLAYLIST" || rm -f "${PLAYLIST}.tmp"
echo "$(date): Updated {name} playlist — $COUNT tracks"
SCRIPT
pct push 127 /tmp/update-{name}-playlist.sh /opt/raido/scripts/update-{name}-playlist.sh
pct exec 127 -- chmod +x /opt/raido/scripts/update-{name}-playlist.sh
pct exec 127 -- bash -c '(crontab -l 2>/dev/null | grep -v "update-{name}-playlist"; echo "*/30 * * * * /opt/raido/scripts/update-{name}-playlist.sh >> /var/log/{name}-playlist.log 2>&1") | crontab -'
```

For **unfiltered stations** (plays all music), just use:
```liquidsoap
{name}_music = playlist(mode="random", reload=300, "/mnt/music")
```

### Full template (Liquidsoap 2.2.x compatible):

```liquidsoap
#!/usr/bin/liquidsoap

# ----- Liquidsoap 2.2.x config for Raido {Display Name} -----

settings.decoder.priorities.ffmpeg := 10
settings.decoder.priorities.mad    := 1

settings.init.allow_root := true
settings.log.level       := 4  # warn

# Telnet control
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := {PORT}

# ---------- Sources ----------
tts_q = request.queue(id="tts_{name}", timeout=30.0, interactive=true)

# Genre-filtered: pre-generated playlist from DB, reloaded every 30 min by cron.
# For unfiltered stations, replace with: playlist(mode="random", reload=300, "/mnt/music")
{name}_music = playlist(
  mode="random",
  reload=1800,
  reload_mode="watch",
  "/shared/{name}_tracks.txt"
)

# Helpers
def meta_get(m, k, d)
  if list.mem(k, list.map(fst, m)) then list.assoc(k, m) else d end
end

last_processed_track = ref("")

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
music = metadata.map(update_metadata, {name}_music)
music_inj = insert_metadata(music)

def track_change_handler(m)
  artist = meta_get(m, "artist", "Unknown artist")
  title  = meta_get(m, "title",  "Unknown title")
  album  = meta_get(m, "album",  "")

  track_key = artist ^ "|" ^ title

  if last_processed_track() != track_key then
    last_processed_track := track_key

    log("🎵 Now playing: " ^ title ^ " by " ^ artist)

    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '","station":"{name}"}'
    url = "http://api:8000/api/v1/liquidsoap/track_change"

    def make_api_call()
      response = http.post(url, data=payload, headers=[("Content-Type", "application/json")])
      log("✅ API call response: " ^ response)
      abs_matches = string.extract(pattern='"artwork_url":"(https?://[^"]+)"', response)
      abs_url = list.assoc(default="", 1, abs_matches)
      rel_matches = string.extract(pattern='"artwork_url":"(/[^"]+)"', response)
      rel_url = list.assoc(default="", 1, rel_matches)
      artwork_url = if abs_url != "" then abs_url
        elsif rel_url != "" then "http://192.168.1.41" ^ rel_url
        else "" end
      if artwork_url != "" then
        music_inj.insert_metadata([("url", artwork_url)])
      end
    end

    thread.run(make_api_call)
  end
end

music = source.on_metadata(music_inj, track_change_handler)

sine_src = sine()
primary = fallback(track_sensitive=true, [tts_q, music])
radio   = fallback(track_sensitive=false, [primary, sine_src])

# ---------- Output ----------
output.icecast(
  %mp3(id3v2=true),
  host="icecast",
  port=8000,
  user="source",
  password="hackme",
  mount="/{name}.mp3",
  name="{Display Name}",
  url="https://raido.local",
  genre="{Genre}",
  description="{description}",
  radio
)

log("🎵 Raido {Display Name} streaming started!")
```

---

## Step 3: Add to `stations.yml`

Add the block **after the last real station** and **before any commented-out stubs**. Do not uncomment existing stubs — they may have wrong ports.

```yaml
  # {Display Name}
  {name}:
    display_name: "{Display Name}"
    identifier: "{name}"
    description: "{description}"

    liquidsoap:
      config_file: "./infra/liquidsoap/{name}.liq"
      telnet_port: {PORT}
      http_port: null
      icecast_mount: "/{name}.mp3"

    dj_worker:
      enabled: true
      default_provider: "ollama"
      default_voice_provider: "kokoro"
      default_voice: "am_onyx"        # or af_bella, af_sky, etc.
      commentary_interval: 1           # every N tracks
      max_seconds: 30
      memory_limit: "1g"
      cpu_limit: "0.50"
      prompt_template: |
        {DJ persona prompt here. Use {{song_title}}, {{artist}}, {{album}}, {{year}} as placeholders.}

    frontend:
      enabled: true
      port: null
      theme: "dark"
      custom_branding: false

    music:
      path: "/mnt/music"
      filter:
        genre: ["{Genre}", "{Genre Variant}"]  # omit filter block if unfiltered
```

---

## Step 4: Add services to `docker-compose.yml`

Insert both services together, adjacent to similar station services (after the last `*-dj-worker` block, before `mb-enricher`):

```yaml
  {name}-liquidsoap:
    image: savonet/liquidsoap:v2.2.5
    restart: unless-stopped
    depends_on: [icecast]
    volumes:
      - /mnt/music:/mnt/music:ro
      - ./infra/liquidsoap/{name}.liq:/{name}.liq:ro
      - shared:/shared
    command: ["liquidsoap","/{name}.liq"]
    ports: ["{PORT}:{PORT}"]

  {name}-dj-worker:
    build: ./services/dj-worker
    restart: unless-stopped
    env_file: .env
    depends_on:
      api:
        condition: service_healthy
    volumes: [shared:/shared]
    environment:
      - STATION_NAME={name}
      - LIQUIDSOAP_HOST={name}-liquidsoap
      - LIQUIDSOAP_PORT={PORT}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://api:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: "1g"
    cpus: "0.50"
```

---

## Step 5: Commit and push

PCT 127 pulls from **GitHub** (remote named `raido`), so you must push to **both** remotes:

```bash
git add infra/liquidsoap/{name}.liq stations.yml docker-compose.yml
git commit -m "feat: add {name} radio station"

git push origin main          # GitHub (PCT 127 pulls from here)
git push gitea main           # Gitea (self-hosted backup)
```

---

## Step 6: Deploy to PCT 127

```bash
pct exec 127 -- bash -c "cd /opt/raido && git pull raido main"
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d {name}-liquidsoap {name}-dj-worker"
```

> **Note:** No rebuild needed — `{name}-liquidsoap` uses the upstream `savonet/liquidsoap` image,
> and `{name}-dj-worker` uses the already-built `dj-worker` image. `up -d` is enough.

---

## Step 7: Verify

```bash
# Containers running?
pct exec 127 -- bash -c "cd /opt/raido && docker compose ps {name}-liquidsoap {name}-dj-worker"

# Liquidsoap started cleanly?
pct exec 127 -- bash -c "cd /opt/raido && docker compose logs {name}-liquidsoap --tail 20"
# Expected: "🎵 Raido {Display Name} streaming started!"

# Stream live on Icecast?
curl -s http://192.168.1.41:8000/{name}.mp3 --max-time 3 -o /dev/null -w "%{http_code}"
# Expected: 200

# API sees the station?
curl -s http://192.168.1.41/api/v1/stations/ | python3 -m json.tool | grep {name}

# Station showing in frontend?
# Open http://192.168.1.41 → hamburger menu → should list {Display Name}
```

---

## Known Gotchas

### DO NOT use `source.on_track` + `skip()` for genre filtering
It looks like it should work but causes a sine beep fallback. When only ~1% of tracks match the genre, the skip loop rapid-fires through hundreds of non-matching tracks, exhausts Liquidsoap's internal request queue, the music source becomes unavailable, and `sine_src` kicks in.

**Use a pre-generated playlist file instead** — see Step 2 above.

### `string.lowercase` does not exist in Liquidsoap v2.2.5
Error: `this value has no method 'lowercase'`
(Only relevant if you're doing any string case checks — not needed with the playlist approach.)

### `docker compose up -d` doesn't restart Liquidsoap if only `.liq` changed
If you push a `.liq` fix after initial deploy, you must explicitly restart:
```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose restart {name}-liquidsoap"
```

### `git pull` fails on PCT 127 due to local changes
```bash
pct exec 127 -- bash -c "cd /opt/raido && git stash && git pull raido main && git stash drop"
```

### Disk space on PCT 127
If `docker compose up` or build fails with "no space left on device":
```bash
pct exec 127 -- bash -c "docker builder prune -f && docker image prune -f"
```

### TTS queue ID must be unique
Each station's `request.queue(id="tts_{name}", ...)` must use a unique id across all `.liq` configs.
Existing: `tts_queue` (main), `tts_christmas`, `tts_recent`, `tts_newreleases`, `tts_jazz`.

---

## Voices reference

Common Kokoro voices:
- `am_onyx` — deep, smooth male (good for jazz, late night)
- `af_bella` — warm female
- `af_sky` — bright female
- `am_michael` — neutral male

---

*Last updated: 2026-03-19 — fixed genre filtering approach (playlist file, not skip loop)*
