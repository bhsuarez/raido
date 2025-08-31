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
# Use a more aggressive timeout and make it interactive
tts_q = request.queue(id="tts", timeout=30.0, interactive=true)

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

# Note: auto_generate_dj_intro and announce_song functions have been
# consolidated into track_change_handler below to avoid duplicate callbacks

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

# Combined callback function that handles both commentary generation and logging
def track_change_handler(m)
  artist = meta_get(m, "artist", "Unknown artist")
  title  = meta_get(m, "title",  "Unknown title")
  album  = meta_get(m, "album",  "")
  
  # Create a unique key for this track
  track_key = artist ^ "|" ^ title
  
  # Only process if this is a different track than last time
  if last_processed_track() != track_key then
    last_processed_track := track_key
    
    log("🎵 Now playing: " ^ title ^ " by " ^ artist)
    log("🏴‍☠️ AUTO-DJ: Requesting intro for upcoming track: " ^ title ^ " by " ^ artist)
    
    # Call our API to trigger both logging and DJ commentary using Liquidsoap's http.post
    payload = '{"artist":"' ^ artist ^ '","title":"' ^ title ^ '","album":"' ^ album ^ '"}'
    url = "http://api:8000/api/v1/liquidsoap/track_change"
    
    # Use thread to avoid blocking liquidsoap
    def make_api_call()
      response = http.post(url, data=payload, headers=[("Content-Type", "application/json")])
      log("✅ API call response: " ^ response)
    end
    
    thread.run(make_api_call)
  end
end

# Attach the combined callback to the music source
music = source.on_metadata(music, track_change_handler)

# Try a simpler approach: rotate between TTS and music using add weights
# This creates a round-robin style approach where TTS plays before tracks

# Sine backup for emergency fallback  
sine_src = sine()

# Create a rotation between TTS and music
# TTS gets priority when available, then falls back to music
primary = fallback(track_sensitive=true, [tts_q, music])

# Log track changes on the primary source for debugging
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
