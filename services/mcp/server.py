import os
import httpx
from mcp.server.fastmcp import FastMCP

RAIDO_API_URL = os.environ.get("RAIDO_API_URL", "http://api:8000")

mcp = FastMCP("Raido", host="0.0.0.0", port=8811)


async def _api_get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=RAIDO_API_URL, timeout=10) as client:
        r = await client.get(path, params=params)
        r.raise_for_status()
        return r.json()


async def _api_post(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=RAIDO_API_URL, timeout=10) as client:
        r = await client.post(path, params=params)
        r.raise_for_status()
        return r.json()


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?:??"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


@mcp.tool()
async def get_now_playing(station: str = "main") -> str:
    """Get the currently playing track on Raido radio station.

    Args:
        station: Station identifier (e.g. "main" or "christmas")
    """
    data = await _api_get("/api/v1/now/", params={"station": station})

    if not data.get("is_playing") or not data.get("track"):
        return f"Nothing is currently playing on the {station} station."

    t = data["track"]
    parts = [f"{t.get('artist', 'Unknown')} - {t.get('title', 'Unknown')}"]

    album_year = []
    if t.get("album"):
        album_year.append(t["album"])
    if t.get("year"):
        album_year.append(str(t["year"]))
    if album_year:
        parts.append(f"({', '.join(album_year)})")

    prog = data.get("progress")
    if prog:
        elapsed = _format_duration(prog.get("elapsed_seconds"))
        total = _format_duration(prog.get("total_seconds"))
        parts.append(f"[{elapsed}/{total}]")

    return " ".join(parts)


@mcp.tool()
async def skip_track(station: str = "main") -> str:
    """Skip the currently playing track on Raido radio station.

    Args:
        station: Station identifier (e.g. "main" or "christmas")
    """
    await _api_post("/api/v1/liquidsoap/skip", params={"station": station})
    # Fetch what's playing now after the skip
    now = await get_now_playing(station)
    return f"Skipped! Now playing: {now}"


@mcp.tool()
async def get_history(station: str = "main", limit: int = 5) -> str:
    """Get recent play history from Raido radio station.

    Args:
        station: Station identifier (e.g. "main" or "christmas")
        limit: Number of recent tracks to return (1-20)
    """
    limit = max(1, min(limit, 20))
    data = await _api_get(
        "/api/v1/now/history", params={"station": station, "limit": limit}
    )

    tracks = data.get("tracks", [])
    if not tracks:
        return f"No play history available for the {station} station."

    lines = [f"Recent tracks on {station} station:"]
    for i, entry in enumerate(tracks, 1):
        t = entry.get("track", {})
        artist = t.get("artist", "Unknown")
        title = t.get("title", "Unknown")
        album = t.get("album")
        year = t.get("year")

        line = f"{i}. {artist} - {title}"
        meta = []
        if album:
            meta.append(album)
        if year:
            meta.append(str(year))
        if meta:
            line += f" ({', '.join(meta)})"

        play = entry.get("play", {})
        if play.get("was_skipped"):
            line += " [skipped]"

        lines.append(line)

    return "\n".join(lines)


@mcp.tool()
async def get_stream_status() -> str:
    """Get the current stream status for Raido radio station including uptime and queue info."""
    data = await _api_get("/api/v1/liquidsoap/status")

    status = data.get("status", "unknown")
    uptime = data.get("uptime_seconds")
    queue = data.get("queue_info", {})

    lines = [f"Stream status: {status}"]
    if uptime is not None:
        hours, rem = divmod(int(uptime), 3600)
        mins, secs = divmod(rem, 60)
        lines.append(f"Uptime: {hours}h {mins}m {secs}s")
    if queue:
        lines.append(f"Queue: {queue}")

    meta = data.get("liquidsoap_metadata", {})
    if meta:
        lines.append(f"Metadata: {meta}")

    return "\n".join(lines)


@mcp.tool()
async def get_dj_voices(station: str = "main") -> str:
    """List available Kokoro TTS voices for the Raido DJ, and show the currently active voice.

    Args:
        station: Station identifier (e.g. "main" or "christmas")
    """
    voices_data = await _api_get("/api/v1/admin/voices")
    settings_data = await _api_get("/api/v1/admin/settings", params={"station": station})

    voices = voices_data.get("voices", [])
    current = settings_data.get("kokoro_voice", "unknown")

    lines = [f"Current DJ voice: **{current}**", f"Available voices ({len(voices)}):", ""]
    lines.extend(f"- {v}" for v in voices)
    return "\n".join(lines)


@mcp.tool()
async def set_dj_voice(voice: str, station: str = "main") -> str:
    """Change the Kokoro TTS voice used by the Raido DJ.

    Args:
        voice: Voice identifier (e.g. "af_bella", "am_michael", "bm_george").
               Use get_dj_voices to see all options.
        station: Station identifier (e.g. "main" or "christmas")
    """
    voices_data = await _api_get("/api/v1/admin/voices")
    available = voices_data.get("voices", [])

    if voice not in available:
        close = [v for v in available if voice.lower() in v.lower()]
        suggestion = f" Did you mean: {', '.join(close[:3])}?" if close else ""
        return f"Voice '{voice}' not found.{suggestion} Use get_dj_voices to see all options."

    async with httpx.AsyncClient(base_url=RAIDO_API_URL, timeout=10) as client:
        r = await client.post(
            "/api/v1/admin/settings",
            params={"station": station},
            json={"kokoro_voice": voice},
        )
        r.raise_for_status()

    return f"DJ voice changed to '{voice}' on the {station} station."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
