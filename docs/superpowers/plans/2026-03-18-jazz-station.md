# Jazz Station Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a jazz radio station to Raido with a genre-filtered Liquidsoap stream, DJ commentary, and Icecast output at `/jazz.mp3`.

**Architecture:** Pure config — no code changes. Three files are touched: a new Liquidsoap `.liq` config, a new entry in `stations.yml`, and two new services in `docker-compose.yml`. The genre filter lives in Liquidsoap via a `skip_non_jazz` function that checks the `genre` ID3 tag on each track and skips non-jazz tracks. The DJ worker runs as a separate container using the existing `dj-worker` image with `STATION_NAME=jazz`.

**Tech Stack:** Liquidsoap 2.2.x, Docker Compose, Icecast, Kokoro TTS, Ollama

---

## Files

| Action | Path | Purpose |
|--------|------|---------|
| Create | `infra/liquidsoap/jazz.liq` | Liquidsoap stream config — genre filter, TTS queue, Icecast output |
| Modify | `stations.yml` | Add `jazz` station block (do NOT use the commented stub at line 113 — it has wrong port 1236) |
| Modify | `docker-compose.yml` | Add `jazz-liquidsoap` and `jazz-dj-worker` services |

---

## Task 1: Create `infra/liquidsoap/jazz.liq`

**Files:**
- Create: `infra/liquidsoap/jazz.liq`

This follows `radio.liq` closely. Key differences: telnet port 1238, TTS queue id `tts_jazz`, `skip_non_jazz` filter (checks `genre` tag), station identifier `"jazz"` in API payload, Icecast mount `/jazz.mp3`.

The `skip_non_jazz` function uses `source.on_track` — same structural pattern as `skip_christmas` in `radio.liq` and `skip_taylor_swift` in `christmas.liq` — but checks `list.assoc(default="", "genre", m)` instead of filename/title/album. Any track whose lowercased genre contains `"jazz"` passes; all others are skipped.

- [ ] **Step 1: Create the file**

```liquidsoap
#!/usr/bin/liquidsoap

# ----- Liquidsoap 2.2.x config for Raido Jazz Lounge -----
# Plays jazz tracks from /mnt/music filtered by genre ID3 tag.
# Tracks whose genre doesn't contain "jazz" (case-insensitive) are skipped.

settings.decoder.priorities.ffmpeg := 10
settings.decoder.priorities.mad    := 1

settings.init.allow_root := true
settings.log.level       := 4  # warn

# Telnet control (port 1238 — after main:1234, christmas:1235, recent:1236, newreleases:1237)
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := 1238

# ---------- Sources ----------
tts_q = request.queue(id="tts_jazz", timeout=30.0, interactive=true)

all_music = playlist(
  mode="random",
  reload=300,
  "/mnt/music"
)

# Skip non-jazz tracks based on genre ID3 tag.
# "jazz" substring covers: Jazz, Smooth Jazz, Bebop, Cool Jazz, Jazz Fusion, etc.
def skip_non_jazz(m)
  genre = string.lowercase(list.assoc(default="", "genre", m))
  is_jazz = string.contains(substring="jazz", genre)
  if not is_jazz then
    log("⏭️ Skipping non-jazz track: " ^ list.assoc(default="", "title", m) ^ " (genre: " ^ genre ^ ")")
    all_music.skip()
  end
end

jazz_music = source.on_track(all_music, skip_non_jazz)

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
music = metadata.map(update_metadata, jazz_music)

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

    log("🎷 Now playing: " ^ title ^ " by " ^ artist)
    log("🎷 AUTO-DJ: Requesting intro for upcoming track: " ^ title ^ " by " ^ artist)

    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '","station":"jazz"}'
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

primary = source.on_track(primary, fun (m) -> log("🎷 Track starting: " ^ meta_get(m, "artist", "Unknown") ^ " - " ^ meta_get(m, "title", "Unknown")))
radio   = fallback(track_sensitive=false, [primary, sine_src])

# ---------- Output ----------
output.icecast(
  %mp3(id3v2=true),
  host="icecast",
  port=8000,
  user="source",
  password="hackme",
  mount="/jazz.mp3",
  name="Jazz Lounge",
  url="https://raido.local",
  genre="Jazz",
  description="Smooth jazz 24/7 — late-night vibes, live commentary",
  radio
)

log("🎷 Raido Jazz Lounge streaming started!")
```

- [ ] **Step 2: Commit**

```bash
git add infra/liquidsoap/jazz.liq
git commit -m "feat: add jazz.liq Liquidsoap config with genre filter"
```

---

## Task 2: Add jazz entry to `stations.yml`

**Files:**
- Modify: `stations.yml`

> **Warning:** There is already a commented-out jazz stub at line ~113 in `stations.yml`. It assigns `telnet_port: 1236`, which conflicts with the `recent` station. Do NOT uncomment that stub. Add the new block as shown below instead.

Add the `jazz:` block inside the `stations:` section, after the `newreleases:` block (around line 111, before the comment block).

- [ ] **Step 1: Add jazz block to `stations.yml`**

Insert the following after the `newreleases:` block and before the `# Example:` comment:

```yaml
  # Jazz station - smooth jazz 24/7
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

- [ ] **Step 2: Commit**

```bash
git add stations.yml
git commit -m "feat: add jazz station to stations.yml"
```

---

## Task 3: Add jazz services to `docker-compose.yml`

**Files:**
- Modify: `docker-compose.yml`

Add two services. Insert them both together after the `newreleases-dj-worker` block (around line 225), before the `mb-enricher:` service. Keep the two jazz services adjacent to each other.

- [ ] **Step 1: Add `jazz-liquidsoap` service**

Insert after the `newreleases-dj-worker` block (before `mb-enricher:`):

```yaml
  jazz-liquidsoap:
    image: savonet/liquidsoap:v2.2.5
    restart: unless-stopped
    depends_on: [icecast]
    volumes:
      - /mnt/music:/mnt/music:ro
      - ./infra/liquidsoap/jazz.liq:/jazz.liq:ro
      - shared:/shared
    command: ["liquidsoap","/jazz.liq"]
    ports: ["1238:1238"]
```

- [ ] **Step 2: Add `jazz-dj-worker` service**

Insert immediately after the `jazz-liquidsoap` block you just added:

```yaml
  jazz-dj-worker:
    build: ./services/dj-worker
    restart: unless-stopped
    env_file: .env
    depends_on:
      api:
        condition: service_healthy
    volumes: [shared:/shared]
    environment:
      - STATION_NAME=jazz
      - LIQUIDSOAP_HOST=jazz-liquidsoap
      - LIQUIDSOAP_PORT=1238
    healthcheck:
      test: ["CMD", "curl", "-f", "http://api:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    mem_limit: "1g"
    cpus: "0.50"
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add jazz-liquidsoap and jazz-dj-worker services"
```

---

## Task 4: Deploy and verify

This runs on the Proxmox host, deploying to PCT 127 (raido).

- [ ] **Step 1: Push to git**

Replace `redesign-with-auth` with your current branch name if it differs.

```bash
git push origin redesign-with-auth
git push gitea redesign-with-auth
```

- [ ] **Step 2: Pull on PCT 127 and start jazz services**

```bash
pct exec 127 -- bash -c "cd /opt/raido && git pull raido redesign-with-auth"
pct exec 127 -- bash -c "cd /opt/raido && docker compose up -d jazz-liquidsoap jazz-dj-worker"
```

Expected: both containers start without error.

- [ ] **Step 3: Verify jazz-liquidsoap started**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose logs jazz-liquidsoap --tail 20"
```

Expected: see `🎷 Raido Jazz Lounge streaming started!` in the logs. If you see errors about the `.liq` file not found or syntax errors, check the volume mount and fix the config.

- [ ] **Step 4: Verify stream is live on Icecast**

```bash
curl -s http://192.168.1.41:8000/jazz.mp3 --max-time 3 -o /dev/null -w "%{http_code}"
```

Expected: `200`. If `404`, check the Icecast mount name in `jazz.liq` matches `/jazz.mp3`.

- [ ] **Step 5: Verify genre filter is working**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose logs jazz-liquidsoap --tail 50"
```

Expected: see `⏭️ Skipping non-jazz track:` entries for non-jazz tracks, and `🎷 Now playing:` entries for jazz tracks. If you see only non-jazz tracks being skipped and no jazz tracks playing, your library may have no files with a `genre` tag containing "jazz" — verify with: `python3 -c "import mutagen; t=mutagen.File('/mnt/music/some_jazz_file.mp3'); print(t.tags)"` on the host.

- [ ] **Step 6: Verify DJ worker is generating commentary**

```bash
pct exec 127 -- bash -c "cd /opt/raido && docker compose logs jazz-dj-worker --tail 30"
```

Expected: after the first track change, see the DJ worker polling and generating a commentary. Wait up to 60s for the first commentary to appear.

- [ ] **Step 7: Verify via API**

```bash
curl -s http://192.168.1.41/api/v1/now/?station=jazz | python3 -m json.tool
```

Expected: JSON with `artist`, `title`, `station: "jazz"` fields.

- [ ] **Step 8: Commit verification complete (no code change — just push final state)**

```bash
git push gitea redesign-with-auth
```
