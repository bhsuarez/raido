# Liquidsoap 2.3.x AI DJ Integration Guide

This guide helps you enhance your current Liquidsoap (2.2.x) setup with the new features in **2.3.x**, tailored for an **AI DJ** that reacts to Icecast metadata.

---

## 🚀 Why Upgrade to 2.3.x for AI DJ Use?

- **Cleaner metadata & track boundaries**  
  Internals rewritten around immutable chunks; more accurate `on_metadata` triggers.

- **Faster startup, lower RAM**  
  Script/stdlib caching reduces startup time and memory.

- **Finer timing resolution**  
  Default frame duration is now **20 ms**, improving timing precision.

---

## 🔧 Example Liquidsoap Script (2.3.x)

```liquidsoap
# --- Settings tuned for 2.3.x behavior ---
set("frame.duration", 0.02)     # finer timing
set("log.level", 3)

# --- Relay input: pull from Icecast with ICY metadata enabled ---
url = "http://user:pass@your-icecast:8000/stream"
s   = input.http(url, icy_metadata=true, restart_on_error=true)

# --- Optional: improve transitions/track detection ---
s = enable_autocue_metadata(s)

# --- Helper: split "Artist - Title" if StreamTitle is all you’ve got ---
def split_streamtitle(mt) =
  artist = mt["artist"] if mt["artist"] != null else ""
  title  = mt["title"]  if mt["title"]  != null else ""

  if (artist == "" and title == "") then
    st = mt["StreamTitle"]
    if st != null then
      parts = string.split(st, " - ")
      artist = list.nth(default="", parts, 0)
      title  = list.nth(default="", parts, 1)
    end
  end
  [( "artist", artist ), ( "title", title )]
end

# --- Emit JSON to a file the AI DJ process reads ---
def write_nowplaying(mt) =
  kv   = split_streamtitle(mt)
  art  = if mt["artwork"] != null then mt["artwork"] else "" end
  url  = if mt["StreamUrl"] != null then mt["StreamUrl"] else "" end
  def esc(s) = string.replace(s, """, "\"") end
  artist = esc(list.assoc("artist", kv))
  title  = esc(list.assoc("title",  kv))
  json = "{"artist":"#{artist}","title":"#{title}","artwork":"#{esc(art)}","streamUrl":"#{esc(url)}","ts":#{float_of_int(int_of_float(time()))}}"
  file.write("/tmp/nowplaying.json", json ^ "\n")
end

s = on_metadata(write_nowplaying, s)

# --- Outputs ---
output.null(s)
```

---

## 📡 How the AI DJ Uses This

- **Reads `/tmp/nowplaying.json`** for `{artist,title}`.  
- Generates commentary with TTS.  
- Fetches album art from MusicBrainz/Discogs/Spotify APIs.  
- Optionally preloads commentary a few hundred ms before track start.

---

## 🛠 Variants for Metadata Delivery

- **HTTP POST:** Replace `file.write` with `system("curl ...")`.  
- **FIFO / Named Pipe:** Write JSON line-by-line for streaming ingestion.  
- **Redis Pub/Sub:** `system("redis-cli PUBLISH nowplaying '#{json}'")`.

---

## 🐳 Docker Example

```bash
docker run --rm   -v $(pwd)/radio.liq:/radio.liq   -v /tmp:/tmp   savonet/liquidsoap:v2.3.3   liquidsoap /radio.liq
```

---

## ⚡ Pro Tips

- **Debounce metadata** if Icecast flaps rapidly.  
- **Autocue** = better crossfade + commentary timing.  
- **Fallbacks** can prevent silence on reconnects.

---

## 📌 Notes for 2.2.x Users

If you’re still on 2.2.x:  
- The script runs, but you **won’t get the improved metadata timing**.  
- Upgrading to 2.3.x (or testing with `rolling-release-v2.3.x`) is recommended.
 
---

## 🧭 Implementation Plan

- Confirm Icecast endpoint and credentials: Verify URL, mountpoint, user/pass, codec, and that ICY metadata is enabled.
- Choose metadata transport method: Default to file at `/tmp/nowplaying.json`; alternatives include HTTP POST or Redis Pub/Sub.
- Write 2.3.x Liquidsoap script: Set `frame.duration`, use `input.http(icy_metadata=true, restart_on_error=true)`, enable `enable_autocue_metadata`, add `on_metadata` hook, and keep `output.null` (or your real output).
- Add JSON writer and debounce: Normalize fields, escape JSON, add timestamp, and rate‑limit to avoid rapid flapping.
- Run Liquidsoap 2.3 in container: Bind `radio.liq` and `/tmp`; use `savonet/liquidsoap:v2.3.x` image.
- Validate nowplaying JSON output: Play multiple tracks and confirm artist/title parsing and timing at transitions.
- Implement AI DJ watcher + TTS: Tail JSON, enrich with artwork/links, synthesize speech (Piper/Azure/Google).
- Integrate TTS audio with ducking: Feed TTS into Liquidsoap via FIFO or `request.queue`; apply ducking during speech.
- Add services, healthchecks, logging: Create `systemd` units for Liquidsoap and the watcher, restart policies, liveness checks, and log rotation.
- Document env vars and runbook: ICECAST URL/creds, file paths, TTS keys; start/stop commands and troubleshooting.

### Debounce Example (Liquidsoap)

```liquidsoap
# Simple guard against rapid duplicate metadata events
last_np = ref("")
last_ts = ref(0.)

def write_nowplaying_debounced(mt) =
  json = (* build your JSON string as in the main example *)
  now = time()
  if json != !last_np or (now - !last_ts) > 3.0 then
    file.write("/tmp/nowplaying.json", json ^ "\n")
    last_np := json
    last_ts := now
  end
end

s = on_metadata(write_nowplaying_debounced, s)
```

### Minimal AI DJ Watcher (pseudo‑Python)

```python
# Reads /tmp/nowplaying.json lines and triggers TTS
import json, time, pathlib, subprocess
p = pathlib.Path("/tmp/nowplaying.json")
seen = ""
while True:
    if not p.exists():
        time.sleep(0.5); continue
    for line in p.read_text().splitlines()[-1:]:
        if line and line != seen:
            data = json.loads(line)
            text = f"Now playing {data.get('title','')} by {data.get('artist','')}"
            # Example with Piper; replace with your TTS
            subprocess.run(["piper", "-m", "en_US-voice.onnx", "-t", text, "-o", "/tmp/dj.wav"]) 
            # Hand off to Liquidsoap via FIFO or HTTP request-harbor
            subprocess.run(["bash", "-lc", "cat /tmp/dj.wav > /tmp/dj.fifo"]) 
            seen = line
    time.sleep(0.5)
```

### Ducking/Voice Integration (Liquidsoap sketch)

```liquidsoap
# Voice comes from a FIFO fed by the watcher
v = input.fifo("/tmp/dj.fifo")
# Your main program/music source is `s`
# Use a basic sidechain duck: lower `s` when `v` is active
s_ducked = ducking(music=s, voice=v, attack=0.2, release=1.2, 
                   threshold=-35., gain=-6.)
output.icecast(%mp3, host="your-icecast", port=8000, password="pass", mount="/stream", s_ducked)
```

### Systemd Units (sketch)

```
# /etc/systemd/system/liquidsoap.service
[Unit]
Description=Liquidsoap 2.3 Radio
After=network-online.target

[Service]
Restart=always
ExecStart=/usr/bin/docker run --rm \
  -v /opt/radio/radio.liq:/radio.liq \
  -v /tmp:/tmp \
  savonet/liquidsoap:v2.3.3 liquidsoap /radio.liq

[Install]
WantedBy=multi-user.target
```

```
# /etc/systemd/system/ai-dj.service
[Unit]
Description=AI DJ Watcher
After=liquidsoap.service

[Service]
WorkingDirectory=/opt/radio
Restart=always
ExecStart=/usr/bin/python3 /opt/radio/ai_dj.py

[Install]
WantedBy=multi-user.target
```

> Replace paths, credentials, and images to match your environment.
