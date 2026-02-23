#!/usr/bin/liquidsoap

# ----- Liquidsoap 2.2.x config for Raido New Arrivals -----
# Plays tracks added to the library in the last 30 days.
# The API writes /shared/recent.m3u hourly with tracks from the last 30 days.
# If the playlist is empty/unavailable, the sine fallback keeps the stream alive.

settings.decoder.priorities.ffmpeg := 10
settings.decoder.priorities.mad    := 1

settings.init.allow_root := true
settings.log.level       := 4  # warn

# Telnet control (different port from main/christmas to avoid conflicts)
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := 1236

# ---------- Sources ----------
tts_q = request.queue(id="tts_recent", timeout=30.0, interactive=true)

# Recent tracks playlist — the API writes and refreshes this file hourly.
# reload=300 + reload_mode="watch" means: pick up changes immediately via
# inotify, with a 5-minute forced reload as a safety net.
recent_music = playlist(
  mode="random",
  reload=300,
  reload_mode="watch",
  "/shared/recent.m3u"
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
music = metadata.map(update_metadata, recent_music)

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

    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '","station":"recent"}'
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
  mount="/recent.mp3",
  name="Raido New Arrivals",
  url="https://raido.local",
  genre="New Arrivals",
  description="Tracks added to Raido in the last 30 days",
  radio
)

log("🆕 Raido New Arrivals streaming started!")
