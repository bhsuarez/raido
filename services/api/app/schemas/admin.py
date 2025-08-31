from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class AdminSettingsResponse(BaseModel):
    dj_commentary_interval: int = 1
    dj_max_seconds: int = 30
    dj_tone: str = "energetic"
    dj_provider: str = "ollama"  # openai, ollama, disabled
    dj_voice_provider: str = "kokoro"  # openai_tts, kokoro, liquidsoap, xtts
    dj_voice_id: Optional[str] = None
    kokoro_voice: Optional[str] = None
    dj_kokoro_voice: Optional[str] = None
    dj_tts_volume: float = 1.0
    kokoro_speed: float = 1.0
    ollama_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://ollama:11434"
    dj_profanity_filter: bool = True
    dj_prompt_template: str = """You're a pirate radio DJ introducing the NEXT song coming up. Create a brief 15-20 second intro for: "{{song_title}}" by {{artist}}{% if album %} from the album "{{album}}"{% endif %}{% if year %} ({{year}}){% endif %}. 

Share ONE interesting fact about the artist, song, or album. Be energetic, knowledgeable, and build excitement for what's coming up next. End with something like "Coming up next!" or "Here we go!" or "Let's dive in!"

Examples of good facts:
- Chart performance or awards
- Recording stories or collaborations  
- Cultural impact or covers by other artists
- Band member changes or solo careers
- Genre innovations or influences

Keep it conversational and exciting. No SSML tags needed."""
    dj_model: str = "llama3.2:1b"  # For Ollama
    dj_temperature: float = 0.8
    dj_max_tokens: int = 200
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
