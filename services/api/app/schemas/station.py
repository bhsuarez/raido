from pydantic import BaseModel, Field
from typing import List, Optional

from .track import TrackRead


class StationBase(BaseModel):
    name: str
    slug: str
    stream_mount: str
    description: Optional[str] = None
    genre: Optional[str] = None
    dj_persona: Optional[str] = None
    artwork_url: Optional[str] = None
    stream_name: Optional[str] = None
    stream_url: Optional[str] = None


class StationCreate(StationBase):
    track_ids: List[int] = Field(default_factory=list)


class StationRead(StationBase):
    id: int
    tracks: List[TrackRead] = Field(default_factory=list)

    class Config:
        orm_mode = True
