from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TrackInfo(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration_sec: Optional[float] = None
    artwork_url: Optional[str] = None
    tags: List[str] = []

class PlayInfo(BaseModel):
    id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    liquidsoap_id: Optional[str] = None
    elapsed_ms: Optional[int] = None
    was_skipped: bool = False

class ProgressInfo(BaseModel):
    elapsed_seconds: int
    total_seconds: int
    percentage: float

class CommentaryInfo(BaseModel):
    id: int
    text: str
    audio_url: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

class NowPlayingResponse(BaseModel):
    is_playing: bool
    track: Optional[TrackInfo] = None
    play: Optional[PlayInfo] = None
    progress: Optional[ProgressInfo] = None

class NextTrackInfo(BaseModel):
    track: TrackInfo
    estimated_start_time: Optional[datetime] = None
    commentary_before: bool = False

class NextUpResponse(BaseModel):
    next_tracks: List[NextTrackInfo] = []
    commentary_scheduled: bool = False
    estimated_start_time: Optional[datetime] = None

class HistoryItem(BaseModel):
    track: TrackInfo
    play: PlayInfo
    commentary: Optional[CommentaryInfo] = None

class HistoryResponse(BaseModel):
    tracks: List[HistoryItem] = []
    total_count: int = 0
    has_more: bool = False

class StreamStatus(BaseModel):
    is_live: bool
    listeners: int = 0
    uptime_seconds: int = 0
    current_bitrate: int = 128
    mount_point: str = "/raido.mp3"