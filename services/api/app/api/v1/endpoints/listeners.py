"""Listener session tracking endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.geoip import lookup_ip
from app.models.listener_session import ListenerSession
from app.models.users import User
from app.schemas.listener import (
    SessionStartRequest,
    SessionStartResponse,
    SessionHeartbeatResponse,
    SessionEndResponse,
)

router = APIRouter()
logger = structlog.get_logger()


def _parse_user_agent(ua_string: Optional[str]) -> dict:
    """Parse user agent string into browser/os/device_type."""
    if not ua_string:
        return {"browser": None, "os": None, "device_type": "desktop"}
    try:
        import user_agents
        ua = user_agents.parse(ua_string)
        device_type = "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
        return {
            "browser": ua.browser.family or None,
            "os": ua.os.family or None,
            "device_type": device_type,
        }
    except Exception:
        return {"browser": None, "os": None, "device_type": "desktop"}


@router.post("/sessions", response_model=SessionStartResponse, status_code=201)
async def start_session(
    payload: SessionStartRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new listener session. Geolocates IP and parses user agent."""
    # Close any existing open sessions for this user (station switch or reconnect)
    now = datetime.now(timezone.utc)
    existing = await db.execute(
        select(ListenerSession).where(
            and_(ListenerSession.user_id == current_user.id, ListenerSession.ended_at.is_(None))
        )
    )
    for session in existing.scalars().all():
        started = session.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        elapsed = (now - started).total_seconds()
        session.ended_at = now
        session.duration_seconds = int(elapsed)

    # Geolocate
    client_ip = request.client.host if request.client else None
    geo = lookup_ip(client_ip)

    # Parse user agent
    ua_string = request.headers.get("User-Agent")
    ua_info = _parse_user_agent(ua_string)

    session = ListenerSession(
        user_id=current_user.id,
        station=payload.station,
        ip_address=client_ip,
        city=geo.city if geo else None,
        region=geo.region if geo else None,
        country=geo.country if geo else None,
        country_code=geo.country_code if geo else None,
        latitude=geo.latitude if geo else None,
        longitude=geo.longitude if geo else None,
        user_agent=ua_string,
        browser=ua_info["browser"],
        os=ua_info["os"],
        device_type=ua_info["device_type"],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info("Listener session started", user_id=current_user.id, station=payload.station)
    return SessionStartResponse(session_id=session.id)


@router.post("/sessions/{session_id}/heartbeat", response_model=SessionHeartbeatResponse)
async def heartbeat(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update last_heartbeat_at for a session owned by the current user."""
    result = await db.execute(
        select(ListenerSession).where(
            and_(
                ListenerSession.id == session_id,
                ListenerSession.user_id == current_user.id,
                ListenerSession.ended_at.is_(None),
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.last_heartbeat_at = datetime.now(timezone.utc)
    await db.commit()
    return SessionHeartbeatResponse(ok=True)


@router.delete("/sessions/{session_id}", response_model=SessionEndResponse)
async def end_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """End a listener session."""
    result = await db.execute(
        select(ListenerSession).where(
            and_(
                ListenerSession.id == session_id,
                ListenerSession.user_id == current_user.id,
                ListenerSession.ended_at.is_(None),
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc)
    started = session.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    duration = int((now - started).total_seconds())
    session.ended_at = now
    session.duration_seconds = duration
    await db.commit()
    return SessionEndResponse(duration_seconds=duration)
