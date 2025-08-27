from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class AdminSettingsResponse(BaseModel):
    dj_commentary_interval: int = 1
    dj_max_seconds: int = 30
    dj_tone: str = "energetic"
    dj_provider: str = "openai"  # openai, ollama, disabled
    dj_voice_provider: str = "openai_tts"
    dj_profanity_filter: bool = True
    station_name: str = "Raido Pirate Radio"
    stream_bitrate: int = 128
    stream_format: str = "mp3"
    crossfade_duration: float = 2.0
    ui_theme: str = "dark"
    ui_show_artwork: bool = True
    ui_history_limit: int = 50
    enable_commentary: bool = True
    enable_track_enrichment: bool = True
    enable_artwork_lookup: bool = True

class AdminStatsResponse(BaseModel):
    total_tracks: int = 0
    total_plays: int = 0
    total_commentary: int = 0
    uptime_seconds: int = 0
    listeners: int = 0
    current_track: Optional[str] = None
    stream_status: str = "offline"
    database_size_mb: float = 0
    cache_size_mb: float = 0