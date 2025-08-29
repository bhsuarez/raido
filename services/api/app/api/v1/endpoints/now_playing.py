from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
import structlog

from app.core.database import get_db
from app.models import Track, Play, Commentary
from app.schemas.stream import NowPlayingResponse, HistoryResponse, NextUpResponse

router = APIRouter()
logger = structlog.get_logger()

@router.get("/", response_model=NowPlayingResponse)
async def get_now_playing(db: AsyncSession = Depends(get_db)):
    """Get currently playing track information"""
    try:
        # Get the most recent play that hasn't ended
        result = await db.execute(
            select(Play, Track)
            .join(Track, Play.track_id == Track.id)
            .where(Play.ended_at.is_(None))
            .order_by(desc(Play.started_at))
            .limit(1)
        )
        
        row = result.first()
        if not row:
            # No current track, try to get the most recent one
            result = await db.execute(
                select(Play, Track)
                .join(Track, Play.track_id == Track.id)
                .order_by(desc(Play.started_at))
                .limit(1)
            )
            row = result.first()
            
            if not row:
                return NowPlayingResponse(
                    is_playing=False,
                    track=None,
                    play=None,
                    progress=None
                )
        
        play, track = row
        
        # Calculate progress if track is currently playing
        progress = None
        if play.ended_at is None:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            elapsed_seconds = (now - play.started_at).total_seconds()
            
            if track.duration_sec and track.duration_sec > 0:
                progress = {
                    "elapsed_seconds": int(elapsed_seconds),
                    "total_seconds": int(track.duration_sec),
                    "percentage": min(100.0, (elapsed_seconds / track.duration_sec) * 100)
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
                "tags": track.tags if isinstance(track.tags, list) else []
            },
            play={
                "id": play.id,
                "started_at": play.started_at,
                "ended_at": play.ended_at,
                "liquidsoap_id": play.liquidsoap_id
            },
            progress=progress
        )
        
    except Exception as e:
        logger.error("Failed to get now playing", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve now playing information")

@router.get("/next", response_model=NextUpResponse)
async def get_next_up(db: AsyncSession = Depends(get_db)):
    """Get information about upcoming tracks from Liquidsoap queue"""
    try:
        import socket
        import asyncio
        from sqlalchemy import func
        
        # Try to get queue info from Liquidsoap first
        liquidsoap_tracks = []
        try:
            # Connect to Liquidsoap telnet
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(("liquidsoap", 1234))
            
            # Get music queue length
            sock.send(b"music.queue\n")
            response = sock.recv(1024).decode().strip()
            queue_length = int(response) if response.isdigit() else 0
            
            sock.close()
            
            logger.info(f"Liquidsoap music queue length: {queue_length}")
            
        except Exception as liq_error:
            logger.warning(f"Could not query Liquidsoap queue: {liq_error}")
            queue_length = 0
        
        # If no queue or small queue, show random tracks that could play next
        if queue_length <= 1:
            # Get some random tracks from the database
            upcoming_query = select(Track).where(
                Track.title != "Unknown"
            ).order_by(func.random()).limit(3)
            
            result = await db.execute(upcoming_query)
            upcoming_tracks = result.scalars().all()
            
            # Format the response
            next_tracks = []
            for track in upcoming_tracks:
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
                        "tags": track.tags if isinstance(track.tags, list) else []
                    },
                    "estimated_start_time": None,
                    "commentary_before": False
                })
        else:
            # Future: Parse actual queue content from Liquidsoap
            # For now, show that tracks are queued
            next_tracks = [{
                "track": {
                    "id": 0,
                    "title": f"{queue_length} tracks queued",
                    "artist": "Liquidsoap Queue",
                    "album": "Coming Up Next",
                    "year": None,
                    "genre": None,
                    "duration_sec": None,
                    "artwork_url": None,
                    "tags": []
                },
                "estimated_start_time": None,
                "commentary_before": False
            }]
        
        return NextUpResponse(
            next_tracks=next_tracks,
            commentary_scheduled=len(next_tracks) > 0,
            estimated_start_time=None
        )
        
    except Exception as e:
        logger.error("Failed to get next up", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve next up information")

@router.get("/history", response_model=HistoryResponse)
async def get_play_history(
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get recent play history"""
    try:
        result = await db.execute(
            select(Play, Track)
            .join(Track, Play.track_id == Track.id)
            .where(Play.ended_at.is_not(None))
            .order_by(desc(Play.started_at))
            .limit(limit)
            .offset(offset)
        )
        
        history = []
        for play, track in result.all():
            # Get any commentary associated with this play
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
                    "tags": track.tags if isinstance(track.tags, list) else []
                },
                "play": {
                    "id": play.id,
                    "started_at": play.started_at,
                    "ended_at": play.ended_at,
                    "elapsed_ms": play.elapsed_ms,
                    "was_skipped": play.was_skipped
                },
                "commentary": {
                    "id": commentary.id,
                    "text": commentary.transcript or commentary.text,
                    "audio_url": commentary.audio_url,
                    "duration_ms": commentary.duration_ms,
                    "created_at": commentary.created_at
                } if commentary else None
            })
        
        return HistoryResponse(
            tracks=history,
            total_count=len(history),
            has_more=len(history) == limit
        )
        
    except Exception as e:
        logger.error("Failed to get play history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve play history")