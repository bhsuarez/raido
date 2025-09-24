from pydantic import BaseModel
from typing import Optional


class TrackRead(BaseModel):
    id: int
    title: str
    artist: str
    album: Optional[str] = None
    genre: Optional[str] = None
    is_christmas: Optional[bool] = None

    class Config:
        orm_mode = True
