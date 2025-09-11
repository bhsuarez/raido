from pydantic import BaseModel
from typing import List, Optional

from .track import TrackRead


class StationBase(BaseModel):
    name: str
    description: Optional[str] = None
    genre: Optional[str] = None
    dj_persona: Optional[str] = None
    artwork_url: Optional[str] = None


class StationCreate(StationBase):
    track_ids: List[int] = []


class StationRead(StationBase):
    id: int
    tracks: List[TrackRead] = []

    class Config:
        orm_mode = True
