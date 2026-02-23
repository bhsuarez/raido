"""Voicing Engine API — Pre-rendered commentary cache management.

Endpoints:
  GET  /voicing/config                  - get worker config/status
  PATCH /voicing/config                 - update worker config (start/stop/limits)
  GET  /voicing/stats                   - progress bar stats
  GET  /voicing/next-unvoiced           - fetch next track without a ready voicing
  GET  /voicing/budget/today            - today's spend
  POST /voicing/budget/record           - record spend (called by worker)
  POST /voicing/progress                - update worker progress (called by worker)
  GET  /voicing/tracks/{track_id}       - get cached voicing for a track
  PATCH /voicing/tracks/{track_id}      - update status (called by worker)
  PUT  /voicing/tracks/{track_id}       - upsert full voicing result (called by worker)
  POST /voicing/tracks/{track_id}/regenerate  - queue regeneration
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import structlog

from app.core.database import get_db
from app.models import Track
from app.models.voicing import TrackVoicingCache, VoicingBudget, VoicingWorkerConfig

router = APIRouter()
logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Worker config / control
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_voicing_config(db: AsyncSession = Depends(get_db)):
    """Return singleton worker config."""
    result = await db.execute(select(VoicingWorkerConfig).where(VoicingWorkerConfig.id == 1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Voicing worker config not found")
    return {
        "id": cfg.id,
        "is_running": cfg.is_running,
        "dry_run_mode": cfg.dry_run_mode,
        "daily_spend_limit_usd": cfg.daily_spend_limit_usd,
        "total_project_limit_usd": cfg.total_project_limit_usd,
        "rate_limit_per_minute": cfg.rate_limit_per_minute,
        "total_tracks_estimated": cfg.total_tracks_estimated,
        "voiced_tracks_count": cfg.voiced_tracks_count,
        "total_spent_usd": cfg.total_spent_usd,
        "last_processed_track_id": cfg.last_processed_track_id,
        "paused_reason": cfg.paused_reason,
        "dry_run_projected_cost_usd": cfg.dry_run_projected_cost_usd,
        "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
    }


@router.patch("/config")
async def update_voicing_config(payload: dict, db: AsyncSession = Depends(get_db)):
    """Update worker config fields (start/stop, limits, dry_run_mode, etc.)."""
    result = await db.execute(select(VoicingWorkerConfig).where(VoicingWorkerConfig.id == 1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=404, detail="Voicing worker config not found")

    allowed = {
        "is_running", "dry_run_mode", "daily_spend_limit_usd", "total_project_limit_usd",
        "rate_limit_per_minute", "total_tracks_estimated", "paused_reason",
        "dry_run_projected_cost_usd",
    }
    for key, value in payload.items():
        if key in allowed:
            setattr(cfg, key, value)

    # When starting fresh, clear paused_reason
    if payload.get("is_running") is True and cfg.paused_reason:
        cfg.paused_reason = None

    await db.commit()
    await db.refresh(cfg)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Stats / progress
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_voicing_stats(db: AsyncSession = Depends(get_db)):
    """Library-wide voicing progress statistics."""
    total_tracks_result = await db.execute(select(func.count(Track.id)))
    total_tracks = total_tracks_result.scalar_one()

    voiced_result = await db.execute(
        select(func.count(TrackVoicingCache.id)).where(TrackVoicingCache.status.in_(["ready", "ready_text_only"]))
    )
    voiced_count = voiced_result.scalar_one()

    failed_result = await db.execute(
        select(func.count(TrackVoicingCache.id)).where(TrackVoicingCache.status == "failed")
    )
    failed_count = failed_result.scalar_one()

    generating_result = await db.execute(
        select(func.count(TrackVoicingCache.id)).where(TrackVoicingCache.status == "generating")
    )
    generating_count = generating_result.scalar_one()

    # Total spend
    spend_result = await db.execute(select(func.sum(VoicingBudget.total_cost_usd)))
    total_spent = spend_result.scalar_one() or 0.0

    # Today's spend
    today_result = await db.execute(
        select(VoicingBudget).where(VoicingBudget.date == date.today())
    )
    today_budget = today_result.scalar_one_or_none()
    daily_spent = today_budget.total_cost_usd if today_budget else 0.0

    # Config
    cfg_result = await db.execute(select(VoicingWorkerConfig).where(VoicingWorkerConfig.id == 1))
    cfg = cfg_result.scalar_one_or_none()

    progress_pct = round(voiced_count / max(total_tracks, 1) * 100, 2)

    return {
        "total_tracks": total_tracks,
        "voiced_count": voiced_count,
        "failed_count": failed_count,
        "generating_count": generating_count,
        "pending_count": max(0, total_tracks - voiced_count - failed_count - generating_count),
        "progress_pct": progress_pct,
        "total_spent_usd": round(total_spent, 5),
        "daily_spent_usd": round(daily_spent, 5),
        "worker_running": cfg.is_running if cfg else False,
        "dry_run_mode": cfg.dry_run_mode if cfg else False,
        "daily_limit_usd": cfg.daily_spend_limit_usd if cfg else 1.0,
        "project_limit_usd": cfg.total_project_limit_usd if cfg else 10.0,
        "paused_reason": cfg.paused_reason if cfg else None,
    }


@router.get("/next-unvoiced")
async def get_next_unvoiced_track(
    after_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return the next track that does not have a ready voicing cache entry.

    Tracks are processed in ascending ID order. `after_id` resumes from a checkpoint.
    """
    # Subquery: track IDs that already have a ready/generating voicing
    voiced_ids_subq = (
        select(TrackVoicingCache.track_id)
        .where(TrackVoicingCache.status.in_(["ready", "ready_text_only", "generating"]))
        .scalar_subquery()
    )

    q = select(Track).where(Track.id.notin_(voiced_ids_subq))
    if after_id:
        q = q.where(Track.id > after_id)
    q = q.order_by(Track.id).limit(1)

    result = await db.execute(q)
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="No unvoiced tracks remaining")

    return {
        "id": track.id,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "year": track.year,
        "genre": track.genre,
        "duration_sec": track.duration_sec,
    }


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

@router.get("/budget/today")
async def get_today_budget(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VoicingBudget).where(VoicingBudget.date == date.today())
    )
    budget = result.scalar_one_or_none()
    if not budget:
        return {"date": date.today().isoformat(), "total_cost_usd": 0.0, "requests_count": 0}
    return {
        "date": budget.date.isoformat(),
        "total_input_tokens": budget.total_input_tokens,
        "total_output_tokens": budget.total_output_tokens,
        "total_cost_usd": budget.total_cost_usd,
        "requests_count": budget.requests_count,
    }


@router.post("/budget/record")
async def record_spend(payload: dict, db: AsyncSession = Depends(get_db)):
    """Called by the voicing worker to record API spend for today."""
    spend_date = date.fromisoformat(payload.get("date", date.today().isoformat()))
    input_tokens = int(payload.get("input_tokens", 0))
    output_tokens = int(payload.get("output_tokens", 0))
    cost_usd = float(payload.get("cost_usd", 0.0))

    result = await db.execute(select(VoicingBudget).where(VoicingBudget.date == spend_date))
    budget = result.scalar_one_or_none()

    if budget is None:
        budget = VoicingBudget(
            date=spend_date,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_cost_usd=cost_usd,
            requests_count=1,
        )
        db.add(budget)
    else:
        budget.total_input_tokens += input_tokens
        budget.total_output_tokens += output_tokens
        budget.total_cost_usd += cost_usd
        budget.requests_count += 1

    await db.commit()
    return {"ok": True}


@router.post("/progress")
async def update_progress(payload: dict, db: AsyncSession = Depends(get_db)):
    """Called by worker to advance the progress checkpoint and total spend."""
    last_id = payload.get("last_processed_track_id")
    cost_usd = float(payload.get("cost_usd", 0.0))

    result = await db.execute(select(VoicingWorkerConfig).where(VoicingWorkerConfig.id == 1))
    cfg = result.scalar_one_or_none()
    if cfg:
        if last_id:
            cfg.last_processed_track_id = last_id
        cfg.voiced_tracks_count = (cfg.voiced_tracks_count or 0) + 1
        cfg.total_spent_usd = (cfg.total_spent_usd or 0.0) + cost_usd
        await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Per-track voicing CRUD
# ---------------------------------------------------------------------------

@router.get("/tracks/{track_id}")
async def get_track_voicing(track_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TrackVoicingCache).where(TrackVoicingCache.track_id == track_id)
    )
    vc = result.scalar_one_or_none()
    if not vc:
        raise HTTPException(status_code=404, detail="No voicing cache for this track")
    return _voicing_to_dict(vc)


@router.patch("/tracks/{track_id}")
async def patch_track_voicing(track_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Partial update — used by worker to flip status."""
    result = await db.execute(
        select(TrackVoicingCache).where(TrackVoicingCache.track_id == track_id)
    )
    vc = result.scalar_one_or_none()
    if vc is None:
        vc = TrackVoicingCache(track_id=track_id, status="pending")
        db.add(vc)

    allowed = {
        "status", "error_message", "genre_persona", "script_text",
        "audio_filename", "audio_duration_sec",
    }
    for key, value in payload.items():
        if key in allowed:
            setattr(vc, key, value)

    await db.commit()
    await db.refresh(vc)
    return _voicing_to_dict(vc)


@router.put("/tracks/{track_id}")
async def upsert_track_voicing(track_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Full upsert — called by worker after successful generation."""
    result = await db.execute(
        select(TrackVoicingCache).where(TrackVoicingCache.track_id == track_id)
    )
    vc = result.scalar_one_or_none()

    if vc is None:
        vc = TrackVoicingCache(track_id=track_id)
        db.add(vc)

    fields = {
        "genre_persona", "script_text", "audio_filename", "audio_duration_sec",
        "provider", "model", "voice_provider", "voice_id",
        "input_tokens", "output_tokens", "estimated_cost_usd", "status", "error_message",
    }
    for key in fields:
        if key in payload:
            setattr(vc, key, payload[key])

    if "status" not in payload:
        vc.status = "ready"

    vc.version = (vc.version or 1) + 1 if vc.id else 1
    await db.commit()
    await db.refresh(vc)
    return _voicing_to_dict(vc)


@router.post("/tracks/{track_id}/regenerate")
async def regenerate_track_voicing(track_id: int, db: AsyncSession = Depends(get_db)):
    """Reset track voicing to 'pending' so the worker will re-process it."""
    # Verify track exists
    track_result = await db.execute(select(Track).where(Track.id == track_id))
    track = track_result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    result = await db.execute(
        select(TrackVoicingCache).where(TrackVoicingCache.track_id == track_id)
    )
    vc = result.scalar_one_or_none()
    if vc:
        vc.status = "pending"
        vc.error_message = None
        vc.script_text = None
        vc.audio_filename = None
    else:
        vc = TrackVoicingCache(track_id=track_id, status="pending")
        db.add(vc)

    await db.commit()
    return {"ok": True, "track_id": track_id, "status": "pending"}


# ---------------------------------------------------------------------------
# Batch status (for MediaLibrary badges)
# ---------------------------------------------------------------------------

@router.get("/tracks/status")
async def batch_voicing_status(
    ids: str = Query(..., description="Comma-separated track IDs"),
    db: AsyncSession = Depends(get_db),
):
    """Return voicing status for a list of track IDs.

    Response: { "<track_id>": "<status>" | null }
    """
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be comma-separated integers")

    if not id_list:
        return {}

    result = await db.execute(
        select(TrackVoicingCache.track_id, TrackVoicingCache.status)
        .where(TrackVoicingCache.track_id.in_(id_list))
    )
    rows = result.all()
    status_map = {str(row.track_id): row.status for row in rows}

    # Fill missing IDs with null
    for tid in id_list:
        if str(tid) not in status_map:
            status_map[str(tid)] = None

    return status_map


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _voicing_to_dict(vc: TrackVoicingCache) -> dict:
    return {
        "id": vc.id,
        "track_id": vc.track_id,
        "genre_persona": vc.genre_persona,
        "script_text": vc.script_text,
        "audio_filename": vc.audio_filename,
        "audio_duration_sec": vc.audio_duration_sec,
        "provider": vc.provider,
        "model": vc.model,
        "voice_provider": vc.voice_provider,
        "voice_id": vc.voice_id,
        "input_tokens": vc.input_tokens,
        "output_tokens": vc.output_tokens,
        "estimated_cost_usd": vc.estimated_cost_usd,
        "status": vc.status,
        "error_message": vc.error_message,
        "version": vc.version,
        "created_at": vc.created_at.isoformat() if vc.created_at else None,
        "updated_at": vc.updated_at.isoformat() if vc.updated_at else None,
    }
