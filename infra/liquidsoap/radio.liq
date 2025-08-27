#!/usr/bin/liquidsoap

# ----- Liquidsoap 2.3.x config for Raido AI Pirate Radio -----
# Decoder prefs
settings.decoder.priorities.ffmpeg := 10
settings.decoder.priorities.mad    := 1

# Core / logging
settings.init.allow_root := true
settings.log.level       := 4  # warn

# Telnet control (used by enqueue scripts to push TTS intros)
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := 1234

# ---------- Sources ----------
# Queue for DJ/TTS lines - this will play intros with timeout
tts_q = request.queue(id="tts", timeout=30.0)

# Fallback playlist for when no music available
backup_music = playlist(
  mode="random",
  reload=300,
  reload_mode="watch", 
  "/mnt/music"
)

# Main music source
all_music = backup_music

# Helpers
def meta_get(m, k, d)
  if list.mem(k, list.map(fst, m)) then list.assoc(k, m) else d end
end

# Global variable to track last processed track (to avoid duplicates)
last_processed_track = ref("")

# Auto-generate DJ intro for upcoming track
def auto_generate_dj_intro(m)
  artist = meta_get(m, "artist", "Unknown Artist")
  title  = meta_get(m, "title",  "Unknown Title")
  
  # Create a unique key for this track
  track_key = artist ^ "|" ^ title
  
  # Only generate if this is a different track than last time
  if last_processed_track() != track_key then
    last_processed_track := track_key
    
    log("🏴‍☠️ AUTO-DJ: Requesting intro for upcoming track: " ^ title ^ " by " ^ artist)
    
    # Call our API to trigger DJ commentary
    url = "http://api:8000/api/v1/liquidsoap/track_change"
    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '"}'
    # Use thread to avoid blocking liquidsoap
    thread.run(fun () -> ignore(http.post(url, data=payload, headers=[("Content-Type", "application/json")])))
  end
end

# Log each song start to API (non-blocking)  
def announce_song(m)
  artist = meta_get(m, "artist", "Unknown artist")
  title  = meta_get(m, "title",  "Unknown title")
  album  = meta_get(m, "album",  "")
  filename = meta_get(m, "filename", "")
  
  log("🎵 Now playing: " ^ title ^ " by " ^ artist)
  
  # Notify our API about track start
  payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '"}'
  cmd = "curl -fsS -X POST -H 'Content-Type: application/json' -d '" ^ payload ^ "' http://api:8000/api/v1/liquidsoap/track_change >/dev/null 2>&1 &"
  ignore(process.run(cmd))
end

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
music = metadata.map(update_metadata, all_music)

# AUTO-DJ: Generate intros when tracks are selected/ready
music = source.on_metadata(music, auto_generate_dj_intro)

# Smooth crossfades on music
music = crossfade(music)

# Announce every real track start
music = source.on_metadata(music, announce_song)

# Sine backup for emergency fallback
sine_src = sine()

# Priority: DJ/TTS first, then music, then sine as emergency fallback
# This ensures intros play before songs
primary = fallback(track_sensitive=true, [tts_q, music])
# Log track changes
primary = source.on_track(primary, fun (m) -> log("🎤 Track starting: " ^ meta_get(m, "artist", "Unknown") ^ " - " ^ meta_get(m, "title", "Unknown")))
radio   = fallback(track_sensitive=false, [primary, sine_src])

# ---------- Output ----------
output.icecast(
  %mp3(id3v2=true),
  host="icecast",
  port=8000,
  user="source",
  password="hackme",
  mount="/raido.mp3",
  name="🏴‍☠️ Raido - AI Pirate Radio",
  url="https://raido.local",
  genre="Pirate Radio",
  description="24/7 AI-powered pirate radio with live DJ commentary",
  radio
)

log("🏴‍☠️ Raido - AI Pirate Radio streaming started!")