"""Pydantic schemas for listener sessions."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    station: str = "main"


class SessionStartResponse(BaseModel):
    session_id: int
    message: str = "Session started"


class SessionHeartbeatResponse(BaseModel):
    ok: bool = True


class SessionEndResponse(BaseModel):
    duration_seconds: Optional[int]


class ListenerSessionRead(BaseModel):
    id: int
    user_id: int
    station: str
    started_at: datetime
    last_heartbeat_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    country_code: Optional[str]
    browser: Optional[str]
    os: Optional[str]
    device_type: Optional[str]

    model_config = {"from_attributes": True}
