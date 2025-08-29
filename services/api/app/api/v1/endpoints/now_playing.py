from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional
import structlog

from app.core.database import get_db
from app.models import Track, Play, Commentary
from app.schemas.stream import NowPlayingResponse, HistoryResponse, NextUpResponse
from app.services.liquidsoap_client import LiquidsoapClient

router = APIRouter()
logger = structlog.get_logger()

@router.get("/", response_model=NowPlayingResponse)
async def get_now_playing(db: AsyncSession = Depends(get_db)):
    """Get currently playing track information"""
    try:
        # Try to read current directly from Liquidsoap (more accurate)
        try:
            client = LiquidsoapClient()
            rids = client.list_request_ids()
            sorted_rids = sorted(rids)
            current_rid = sorted_rids[0] if sorted_rids else None
            if current_rid is not None:
                ls_meta = client.get_request_metadata(current_rid)
                if (ls_meta.get('source') or '').lower() != 'tts':
                    filename = ls_meta.get("filename") or ls_meta.get("initial_uri")
                    track: Optional[Track] = None
                    if filename:
                        result = await db.execute(select(Track).where(Track.file_path == filename))
                        track = result.scalar_one_or_none()
                        if not track:
                            result = await db.execute(select(Track).where(Track.file_path.endswith(filename)))
                            track = result.scalar_one_or_none()
                    if not track:
                        title = ls_meta.get("title")
                        artist = ls_meta.get("artist")
                        if title and artist:
                            result = await db.execute(select(Track).where(Track.title == title, Track.artist == artist))
                            track = result.scalar_one_or_none()

                    if track:
                        payload = {
                            "id": track.id,
                            "title": track.title,
                            "artist": track.artist,
                            "album": track.album,
                            "year": track.year,
                            "genre": track.genre,
                            "duration_sec": track.duration_sec,
                            "artwork_url": track.artwork_url,
                            "tags": track.tags if isinstance(track.tags, list) else [],
                        }
                        duration = float(track.duration_sec) if track.duration_sec else None
                    else:
                        year_int = None
                        if ls_meta.get("year") and str(ls_meta.get("year")).isdigit():
                            year_int = int(ls_meta.get("year"))
                        payload = {
                            "id": 0,
                            "title": ls_meta.get("title") or "Unknown",
                            "artist": ls_meta.get("artist") or "Unknown Artist",
                            "album": ls_meta.get("album"),
                            "year": year_int,
                            "genre": ls_meta.get("genre"),
                            "duration_sec": None,
                            "artwork_url": None,
                            "tags": [],
                        }
                        duration = None

                    # Compute progress if possible using on_air_timestamp
                    progress = None
                    try:
                        ts = ls_meta.get("on_air_timestamp")
                        if ts is None:
                            on_air_str = ls_meta.get("on_air")
                            if on_air_str:
                                from datetime import datetime
                                started = datetime.strptime(on_air_str, "%Y/%m/%d %H:%M:%S")
                            else:
                                started = None
                        else:
                            from datetime import datetime, timezone
                            started = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                        if started:
                            from datetime import datetime, timezone
                            now = datetime.now(timezone.utc)
                            elapsed_seconds = max(0, int((now - started).total_seconds()))
                            if duration and duration > 0:
                                progress = {
                                    "elapsed_seconds": elapsed_seconds,
                                    "total_seconds": int(duration),
                                    "percentage": min(100.0, (elapsed_seconds / duration) * 100),
                                }
                    except Exception:
                        progress = None

                    return NowPlayingResponse(
                        is_playing=True,
                        track=payload,  # type: ignore
                        play=None,
                        progress=progress,
                    )
        except Exception:
            pass

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
async def get_next_up(limit: int = 1, db: AsyncSession = Depends(get_db)):
    """Get information about the next upcoming track based on Liquidsoap request queue.

    Falls back to a random pick when queue introspection fails.
    """
    try:
        # Try to determine next track from Liquidsoap request queue (RID order)
        client = LiquidsoapClient()

        # Compute base estimated start from current play progress if possible
        current_row = await db.execute(
            select(Play, Track)
            .join(Track, Play.track_id == Track.id)
            .where(Play.ended_at.is_(None))
            .order_by(desc(Play.started_at))
            .limit(1)
        )
        cur = current_row.first()
        base_now = None
        base_remaining = 0.0
        if cur:
            cur_play, cur_track = cur
            from datetime import datetime, timezone
            base_now = datetime.now(timezone.utc)
            if cur_track.duration_sec and cur_play.started_at:
                elapsed = (base_now - cur_play.started_at).total_seconds()
                base_remaining = max(0.0, float(cur_track.duration_sec) - elapsed)

        # Inspect Liquidsoap request queue and build next N items
        rids = client.list_request_ids()
        sorted_rids = sorted(rids)
        # Fast path: avoid per-RID telnet metadata calls; use ordering semantics
        base_current = sorted_rids[0] if sorted_rids else None
        # Choose the next sequential RIDs after the current one (matches observed telnet behavior)
        next_rids: list[int] = []
        if base_current is not None:
            next_rids = [rid for rid in sorted_rids if rid > base_current]

        next_rids = next_rids[: max(0, min(limit, 10))]  # cap to 10

        if next_rids:
            from datetime import timedelta
            next_tracks = []
            cumulative = base_remaining if base_now else 0.0

            for rid in next_rids:
                ls_meta = client.get_request_metadata(rid)
                # Map to DB
                filename = ls_meta.get("filename") or ls_meta.get("initial_uri")
                track: Optional[Track] = None
                if filename:
                    result = await db.execute(select(Track).where(Track.file_path == filename))
                    track = result.scalar_one_or_none()
                    if not track:
                        result = await db.execute(select(Track).where(Track.file_path.endswith(filename)))
                        track = result.scalar_one_or_none()
                if not track:
                    title = ls_meta.get("title")
                    artist = ls_meta.get("artist")
                    if title and artist:
                        result = await db.execute(select(Track).where(Track.title == title, Track.artist == artist))
                        track = result.scalar_one_or_none()

                if track:
                    payload = {
                        "id": track.id,
                        "title": track.title,
                        "artist": track.artist,
                        "album": track.album,
                        "year": track.year,
                        "genre": track.genre,
                        "duration_sec": track.duration_sec,
                        "artwork_url": track.artwork_url,
                        "tags": track.tags if isinstance(track.tags, list) else [],
                    }
                    duration = float(track.duration_sec) if track.duration_sec else None
                else:
                    year_int = None
                    if ls_meta.get("year") and str(ls_meta.get("year")).isdigit():
                        year_int = int(ls_meta.get("year"))
                    payload = {
                        "id": 0,
                        "title": ls_meta.get("title") or "Unknown",
                        "artist": ls_meta.get("artist") or "Unknown Artist",
                        "album": ls_meta.get("album"),
                        "year": year_int,
                        "genre": ls_meta.get("genre"),
                        "duration_sec": None,
                        "artwork_url": None,
                        "tags": [],
                    }
                    # LS metadata rarely includes duration; keep None
                    duration = None

                est = None
                if base_now is not None:
                    est = base_now + timedelta(seconds=cumulative)
                next_tracks.append({
                    "track": payload,
                    "estimated_start_time": est,
                    "commentary_before": False,
                })

                if duration:
                    cumulative += duration

            logger.info("Next up list from LS queue", count=len(next_tracks), rids=next_rids)

            return NextUpResponse(
                next_tracks=next_tracks,
                commentary_scheduled=len(next_tracks) > 0,
                estimated_start_time=next_tracks[0]["estimated_start_time"] if next_tracks else None,
            )

        # Fallback: random pick excluding recent plays
        from sqlalchemy import func
        from datetime import timedelta
        estimated_start = (base_now + timedelta(seconds=base_remaining)) if base_now else None
        recent_plays_result = await db.execute(
            select(Play.track_id).order_by(Play.started_at.desc()).limit(10)
        )
        recent_track_ids = [row[0] for row in recent_plays_result.fetchall()]
        upcoming_query = select(Track).where(
            Track.title != "Unknown",
            ~Track.id.in_(recent_track_ids) if recent_track_ids else True,
        ).order_by(func.random()).limit(1)

        result = await db.execute(upcoming_query)
        next_track = result.scalar_one_or_none()
        if next_track:
            next_tracks = [{
                "track": {
                    "id": next_track.id,
                    "title": next_track.title,
                    "artist": next_track.artist,
                    "album": next_track.album,
                    "year": next_track.year,
                    "genre": next_track.genre,
                    "duration_sec": next_track.duration_sec,
                    "artwork_url": next_track.artwork_url,
                    "tags": next_track.tags if isinstance(next_track.tags, list) else [],
                },
                "estimated_start_time": estimated_start,
                "commentary_before": False,
            }]
        else:
            next_tracks = []

        logger.info(
            "Generated fallback random next up",
            next_track_id=next_track.id if next_track else None,
            title=next_track.title if next_track else None,
        )

        return NextUpResponse(
            next_tracks=next_tracks,
            commentary_scheduled=len(next_tracks) > 0,
            estimated_start_time=estimated_start,
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
