from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, Dict, Any
import structlog

from app.core.database import get_db
from app.models import Track, Play, Commentary, Station
from app.schemas.stream import NowPlayingResponse, HistoryResponse, NextUpResponse

router = APIRouter()
logger = structlog.get_logger()

@router.get("/", response_model=NowPlayingResponse)
async def get_now_playing(
    station_slug: str = "main",
    db: AsyncSession = Depends(get_db),
):
    """Get currently playing track information for a specific station."""

    normalized_slug = (station_slug or "main").strip().lower()

    try:
        station_result = await db.execute(select(Station).where(Station.slug == normalized_slug))
        station = station_result.scalar_one_or_none()
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{normalized_slug}' not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve station", error=str(exc), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to resolve station")

    try:
        result = await db.execute(
            select(Play, Track)
            .join(Track, Play.track_id == Track.id)
            .where(Play.station_id == station.id)
            .order_by(desc(Play.started_at))
            .limit(1)
        )
        row = result.first()

        if not row:
            return NowPlayingResponse(
                is_playing=False,
                track=None,
                play=None,
                progress=None,
                station_slug=station.slug,
                station_name=station.name,
            )

        play, track = row

        progress = None
        if play.ended_at is None and track.duration_sec and track.duration_sec > 0:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            elapsed_seconds = max(0, (now - play.started_at).total_seconds())
            progress = {
                "elapsed_seconds": int(elapsed_seconds),
                "total_seconds": int(track.duration_sec),
                "percentage": min(100.0, (elapsed_seconds / track.duration_sec) * 100),
            }

        return NowPlayingResponse(
            is_playing=play.ended_at is None,
            track={
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "year": track.year,
                "genre": track.genre,
                "duration_sec": track.duration_sec,
                "artwork_url": track.artwork_url,
                "tags": track.tags if isinstance(track.tags, list) else [],
                "is_christmas": bool(getattr(track, 'is_christmas', False)),
            },
            play={
                "id": play.id,
                "started_at": play.started_at,
                "ended_at": play.ended_at,
                "liquidsoap_id": play.liquidsoap_id,
                "station_slug": station.slug,
            },
            progress=progress,
            station_slug=station.slug,
            station_name=station.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get now playing", error=str(e), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to retrieve now playing information")

@router.get("/next", response_model=NextUpResponse)
async def get_next_up(
    limit: int = 1,
    station_slug: str = "main",
    db: AsyncSession = Depends(get_db),
):
    """Return upcoming tracks for the requested station."""

    normalized_slug = (station_slug or "main").strip().lower()

    try:
        station_result = await db.execute(select(Station).where(Station.slug == normalized_slug))
        station = station_result.scalar_one_or_none()
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{normalized_slug}' not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve station for next up", error=str(exc), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to resolve station")

    try:
        recent_result = await db.execute(
            select(Play.track_id)
            .where(Play.station_id == station.id)
            .order_by(desc(Play.started_at))
            .limit(25)
        )
        recent_track_ids = [row[0] for row in recent_result.fetchall() if row[0] is not None]

        track_query = (
            select(Track)
            .join(Track.stations)
            .where(Station.id == station.id)
            .where(Track.title != "Unknown")
        )
        if recent_track_ids:
            track_query = track_query.where(~Track.id.in_(recent_track_ids))

        track_query = track_query.order_by(func.random()).limit(max(1, limit))
        track_result = await db.execute(track_query)
        tracks = track_result.scalars().all()

        next_tracks = []
        for track in tracks:
            next_tracks.append({
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "year": track.year,
                    "genre": track.genre,
                    "duration_sec": track.duration_sec,
                    "artwork_url": track.artwork_url,
                    "tags": track.tags if isinstance(track.tags, list) else [],
                    "is_christmas": bool(getattr(track, 'is_christmas', False)),
                },
                "estimated_start_time": None,
                "commentary_before": False,
            })

        return NextUpResponse(
            next_tracks=next_tracks,
            commentary_scheduled=len(next_tracks) > 0,
            estimated_start_time=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get next up", error=str(e), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to retrieve next up information")
@router.get("/history", response_model=HistoryResponse)
async def get_play_history(
    limit: int = 10,
    offset: int = 0,
    station_slug: str = "main",
    db: AsyncSession = Depends(get_db),
):
    """Get recent play history for a station."""

    normalized_slug = (station_slug or "main").strip().lower()

    try:
        station_result = await db.execute(select(Station).where(Station.slug == normalized_slug))
        station = station_result.scalar_one_or_none()
        if not station:
            raise HTTPException(status_code=404, detail=f"Station '{normalized_slug}' not found")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to resolve station for history", error=str(exc), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to resolve station")

    try:
        result = await db.execute(
            select(Play, Track)
            .join(Track, Play.track_id == Track.id)
            .where(Play.station_id == station.id)
            .where(Play.ended_at.is_not(None))
            .order_by(desc(Play.started_at))
            .limit(limit)
            .offset(offset)
        )

        history = []
        for play, track in result.all():
            commentary_result = await db.execute(
                select(Commentary)
                .where(Commentary.play_id == play.id)
                .where(Commentary.status == "ready")
                .limit(1)
            )
            commentary = commentary_result.scalar_one_or_none()

            history.append({
                "track": {
                    "id": track.id,
                    "title": track.title,
                    "artist": track.artist,
                    "album": track.album,
                    "year": track.year,
                    "genre": track.genre,
                    "duration_sec": track.duration_sec,
                    "artwork_url": track.artwork_url,
                    "tags": track.tags if isinstance(track.tags, list) else [],
                    "is_christmas": bool(getattr(track, 'is_christmas', False)),
                },
                "play": {
                    "id": play.id,
                    "started_at": play.started_at,
                    "ended_at": play.ended_at,
                    "elapsed_ms": play.elapsed_ms,
                    "was_skipped": play.was_skipped,
                    "station_slug": station.slug,
                },
                "commentary": {
                    "id": commentary.id,
                    "text": commentary.transcript or commentary.text,
                    "audio_url": commentary.audio_url,
                    "duration_ms": commentary.duration_ms,
                    "created_at": commentary.created_at,
                } if commentary else None,
            })

        return HistoryResponse(
            tracks=history,
            total_count=len(history),
            has_more=len(history) == limit,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get play history", error=str(e), station_slug=normalized_slug)
        raise HTTPException(status_code=500, detail="Failed to retrieve play history")
