from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrackRead(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration_sec: Optional[float] = None
    bitrate: Optional[int] = None
    artwork_url: Optional[str] = None
    genre: Optional[str] = None
    file_path: str
    play_count: int = 0
    recording_mbid: Optional[str] = None
    release_mbid: Optional[str] = None
    last_played_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrackUpdate(BaseModel):
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    artwork_url: Optional[str] = None
    genre: Optional[str] = None
    recording_mbid: Optional[str] = None
    release_mbid: Optional[str] = None


class MBCandidate(BaseModel):
    recording_mbid: str
    release_mbid: Optional[str] = None
    title: str
    artist: str
    album: Optional[str] = None
    year: Optional[int] = None
    country: Optional[str] = None
    label: Optional[str] = None
    artwork_url: Optional[str] = None
    genre: Optional[str] = None


class StationInfo(BaseModel):
    identifier: str
    name: str


class TrackFacets(BaseModel):
    genres: List[str]
    artists: List[str]
    albums: List[str]
    stations: List[StationInfo]
