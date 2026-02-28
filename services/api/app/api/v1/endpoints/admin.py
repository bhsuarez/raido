from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone, timedelta
import structlog
from collections import Counter
import re
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.schemas.admin import AdminSettingsResponse, AdminStatsResponse
from app.models import Commentary, Play, Setting, Track
import httpx
try:
    from jinja2 import Template, TemplateSyntaxError
except Exception:
    Template = None  # type: ignore
    TemplateSyntaxError = Exception  # type: ignore

router = APIRouter()

@router.get("/settings", response_model=AdminSettingsResponse)
async def get_admin_settings(
    station: str = Query("main", description="Station identifier (main, christmas, etc.)"),
    db: AsyncSession = Depends(get_db)
):
    """Get admin settings for a specific station"""
    try:
        logger = structlog.get_logger()

        # Get settings for the specified station
        result = await db.execute(select(Setting).where(Setting.station == station))
        settings = result.scalars().all()
        
        # Build settings dict with defaults
        settings_dict = {}
        for setting in settings:
            if setting.value_type == "bool":
                settings_dict[setting.key] = setting.value.lower() in ["true", "1", "yes"]
            elif setting.value_type == "int":
                settings_dict[setting.key] = int(setting.value)
            elif setting.value_type == "float":
                settings_dict[setting.key] = float(setting.value)
            else:
                # Don't include settings with string "None" - let Pydantic use defaults
                if setting.value != "None":
                    settings_dict[setting.key] = setting.value
        
        # Create response with database values or defaults
        return AdminSettingsResponse(**settings_dict)
        
    except Exception as e:
        logger.error("Failed to get settings", error=str(e))
        # Return defaults on error
        return AdminSettingsResponse()

## Deprecated older voices endpoint removed in favor of settings-aware implementation below

@router.post("/settings")
async def update_admin_settings(
    settings: Dict[str, Any],
    station: str = Query("main", description="Station identifier (main, christmas, etc.)"),
    db: AsyncSession = Depends(get_db)
):
    """Update admin settings for a specific station"""
    try:
        logger = structlog.get_logger()

        # Pre-validate known complex settings to avoid saving invalid values
        if 'dj_prompt_template' in settings:
            raw_template = str(settings['dj_prompt_template'] or '')
            # Basic length guard
            if len(raw_template) > 5000:
                raise HTTPException(status_code=400, detail="dj_prompt_template is too long (max 5000 chars)")
            # Validate Jinja2 syntax if available
            if Template is not None:
                try:
                    Template(raw_template)  # type: ignore
                except TemplateSyntaxError as te:  # type: ignore
                    raise HTTPException(status_code=400, detail=f"Invalid prompt template syntax: {te}")
            else:
                logger.warning("Jinja2 not available in API container; skipping template validation")

        for key, value in settings.items():
            # Check if setting exists for this station
            result = await db.execute(
                select(Setting).where(Setting.key == key, Setting.station == station)
            )
            existing_setting = result.scalar_one_or_none()

            if existing_setting:
                # Update existing setting
                existing_setting.value = str(value)
                existing_setting.updated_at = datetime.now(timezone.utc)
            else:
                # Create new setting with type inference
                value_type = "string"
                if isinstance(value, bool):
                    value_type = "bool"
                elif isinstance(value, int):
                    value_type = "int"
                elif isinstance(value, float):
                    value_type = "float"

                # Determine category from key
                category = "general"
                if key.startswith("dj_"):
                    category = "dj"
                elif key.startswith("stream_"):
                    category = "stream"
                elif key.startswith("ui_"):
                    category = "ui"
                elif key.startswith("enable_"):
                    category = "features"

                new_setting = Setting(
                    key=key,
                    value=str(value),
                    value_type=value_type,
                    category=category,
                    station=station,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(new_setting)

        await db.commit()
        logger.info("Settings updated", station=station, count=len(settings))

        return {"status": "success", "message": f"Updated {len(settings)} settings for {station} station"}

    except Exception as e:
        logger.error("Failed to update settings", station=station, error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    """Get admin statistics"""
    # For now, return default stats
    # In a real implementation, this would query various tables for statistics
    return AdminStatsResponse()

@router.post("/commentary")
async def create_commentary(
    commentary_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new commentary record"""
    try:
        logger = structlog.get_logger()
        
        # Get the current play record if play_id is provided
        play_id = commentary_data.get("play_id")
        if play_id:
            # Verify the play record exists
            result = await db.execute(select(Play).where(Play.id == play_id))
            play = result.scalar_one_or_none()
            if not play:
                raise HTTPException(status_code=404, detail="Play record not found")
        
        # Process audio URL to include full path
        audio_url = commentary_data.get("audio_url")
        if audio_url and not audio_url.startswith("http") and not audio_url.startswith("/"):
            # Convert filename to full static URL
            audio_url = f"/static/tts/{audio_url}"
        
        # Normalize context payload so station filters work across multiple stations
        raw_context = commentary_data.get("context_data")
        context_data: Optional[Dict[str, Any]] = None
        if isinstance(raw_context, dict):
            context_data = raw_context
        elif raw_context is not None:
            logger.warning(
                "Dropping non-dict context_data payload",
                context_type=type(raw_context).__name__,
            )

        # Create commentary record
        status_val = commentary_data.get("status") or "ready"
        commentary = Commentary(
            play_id=play_id,
            text=commentary_data.get("text", ""),
            transcript=commentary_data.get("transcript"),
            audio_url=audio_url,
            provider=commentary_data.get("provider", "ollama"),
            model=commentary_data.get("model"),
            voice_provider=commentary_data.get("voice_provider", "kokoro"),
            voice_id=commentary_data.get("voice_id"),
            duration_ms=commentary_data.get("duration_ms"),
            generation_time_ms=commentary_data.get("generation_time_ms"),
            tts_time_ms=commentary_data.get("tts_time_ms"),
            status=status_val,
            context_data=context_data,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(commentary)
        await db.commit()
        await db.refresh(commentary)
        
        logger.info("Commentary created successfully", 
                   commentary_id=commentary.id, 
                   play_id=play_id,
                   audio_url=commentary.audio_url)
        
        return {
            "status": "success",
            "message": "Commentary created",
            "commentary_id": commentary.id,
            "audio_url": commentary.audio_url,
            "status_val": commentary.status,
        }
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.error("Failed to create commentary", error=str(e), data=commentary_data)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create commentary: {str(e)}")

@router.patch("/commentary/{commentary_id}")
async def update_commentary(
    commentary_id: int,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update fields on a commentary record (status, audio_url, timings, text, etc.)."""
    logger = structlog.get_logger()
    try:
        # Fetch the commentary
        from sqlalchemy import select
        result = await db.execute(select(Commentary).where(Commentary.id == commentary_id))
        commentary = result.scalar_one_or_none()
        if not commentary:
            raise HTTPException(status_code=404, detail="Commentary not found")

        # Update whitelisted fields if present
        fields = [
            "text", "ssml", "transcript", "audio_url", "provider", "model",
            "voice_provider", "voice_id", "duration_ms", "generation_time_ms",
            "tts_time_ms", "status", "error_message", "retry_count", "context_data"
        ]
        for key in fields:
            if key in payload:
                setattr(commentary, key, payload[key])

        commentary.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"status": "success", "updated_id": commentary_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update commentary", error=str(e), commentary_id=commentary_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update commentary: {str(e)}")

@router.delete("/commentary/{commentary_id}")
async def delete_commentary(
    commentary_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a commentary record and its local audio file if present."""
    logger = structlog.get_logger()
    try:
        # Fetch the commentary
        result = await db.execute(select(Commentary).where(Commentary.id == commentary_id))
        commentary = result.scalar_one_or_none()
        if not commentary:
            raise HTTPException(status_code=404, detail="Commentary not found")

        # Attempt to remove local audio file if it's a local path
        audio_url = commentary.audio_url or ""
        file_deleted = False
        try:
            import os
            file_path = None
            if audio_url.startswith("/static/tts/"):
                filename = audio_url.split("/")[-1]
                file_path = f"/shared/tts/{filename}"
            elif audio_url and not audio_url.startswith("http") and not audio_url.startswith("/"):
                # Audio stored as plain filename
                file_path = f"/shared/tts/{audio_url}"
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                file_deleted = True
        except Exception as fe:
            logger.warning("Failed to delete commentary audio file", error=str(fe), audio_url=audio_url)

        # Delete DB record
        await db.delete(commentary)
        await db.commit()

        return {"status": "success", "deleted_id": commentary_id, "file_deleted": file_deleted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete commentary", error=str(e), commentary_id=commentary_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete commentary: {str(e)}")

@router.get("/tts-status")
async def get_tts_status(
    db: AsyncSession = Depends(get_db),
    window_hours: int = Query(1, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    station: str = Query(
        "main",
        description="Station identifier (main, christmas, etc.). Use 'all' to include every station.",
    ),
):
    """Get TTS generation status and statistics"""
    try:
        logger = structlog.get_logger()
        
        # Get recent commentary records with generation stats
        from sqlalchemy import func, desc, update
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        window_start = now - timedelta(hours=window_hours)

        # Cleanup stuck generations older than 30 seconds
        stuck_threshold = now - timedelta(seconds=30)
        await db.execute(
            update(Commentary)
            .where(Commentary.status.in_(["pending", "generating", "running"]))
            .where(Commentary.created_at < stuck_threshold)
            .values(status="failed", error_message="Timed out", updated_at=now)
        )
        await db.commit()
        
        station_normalized = (station or "main").lower()

        # Helper to scope queries to a station when requested
        def apply_station_filter(stmt):
            if station_normalized == "all":
                return stmt

            station_value = func.lower(
                func.coalesce(
                    Commentary.context_data.op('->>')('station_name'),
                    Commentary.context_data.op('->>')('station'),
                    'main',
                )
            )
            return stmt.where(station_value == station_normalized)

        # Count total commentary in last 24h
        total_query = select(func.count(Commentary.id)).where(Commentary.created_at >= last_24h)
        total_result = await db.execute(apply_station_filter(total_query))
        total_24h = total_result.scalar() or 0
        
        # Count successful commentary in last 24h
        success_query = (
            select(func.count(Commentary.id))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.status == "ready")
        )
        success_result = await db.execute(apply_station_filter(success_query))
        success_24h = success_result.scalar() or 0
        
        # Count failed commentary in last 24h
        failed_query = (
            select(func.count(Commentary.id))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.status == "failed")
        )
        failed_result = await db.execute(apply_station_filter(failed_query))
        failed_24h = failed_result.scalar() or 0
        
        # Get recent activity with pagination
        recent_query = (
            select(Commentary)
            .where(Commentary.created_at >= window_start)
            .order_by(desc(Commentary.created_at))
            .limit(limit)
            .offset(offset)
        )
        recent_result = await db.execute(apply_station_filter(recent_query))
        recent_commentary = recent_result.scalars().all()

        # Get total count of records in the window for pagination
        count_query = select(func.count(Commentary.id)).where(Commentary.created_at >= window_start)
        count_result = await db.execute(apply_station_filter(count_query))
        total_count = count_result.scalar() or 0

        # Get average generation times
        avg_gen_time_query = (
            select(func.avg(Commentary.generation_time_ms))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.generation_time_ms.is_not(None))
        )
        avg_gen_time_result = await db.execute(apply_station_filter(avg_gen_time_query))
        avg_gen_time = avg_gen_time_result.scalar() or 0
        
        avg_tts_time_query = (
            select(func.avg(Commentary.tts_time_ms))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.tts_time_ms.is_not(None))
        )
        avg_tts_time_result = await db.execute(apply_station_filter(avg_tts_time_query))
        avg_tts_time = avg_tts_time_result.scalar() or 0
        
        # Format recent activity (return full text; UI can decide how to render)
        recent_activity = []
        for comment in recent_commentary:
            # Try to surface LLM mode info if present in context_data
            llm_mode = None
            try:
                if comment.context_data and isinstance(comment.context_data, dict):
                    llm_mode = comment.context_data.get('ollama_mode')
            except Exception:
                llm_mode = None

            # Map database status to frontend status
            frontend_status = comment.status
            if comment.status in ["pending", "generating"]:
                frontend_status = "running"
            elif comment.status == "ready":
                frontend_status = "ready"
            elif comment.status == "failed":
                frontend_status = "failed"

            # Ensure audio_url has full static path
            audio_url = comment.audio_url
            if audio_url and not audio_url.startswith("http") and not audio_url.startswith("/"):
                audio_url = f"/static/tts/{audio_url}"

            recent_activity.append({
                "id": comment.id,
                "text": comment.text,  # may contain SSML
                "transcript": comment.transcript,  # full plain-text transcript when available
                "status": frontend_status,
                "provider": comment.provider,
                "voice_provider": comment.voice_provider,
                "voice_id": comment.voice_id,
                "generation_time_ms": comment.generation_time_ms,
                "tts_time_ms": comment.tts_time_ms,
                "created_at": comment.created_at,
                "audio_url": audio_url,
                "llm_mode": llm_mode
            })
        
        # Determine chatterbox health
        def _normalize_base(value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            cleaned = value.strip()
            if not cleaned:
                return None
            return cleaned.rstrip('/')

        chatterbox_candidates: List[str] = []
        seen_candidates: Set[str] = set()

        def _add_candidate(raw: Optional[str]) -> None:
            base = _normalize_base(raw)
            if base and base not in seen_candidates:
                seen_candidates.add(base)
                chatterbox_candidates.append(base)

        _add_candidate(getattr(settings, 'CHATTERBOX_BASE_URL', None))

        db_base_result = await db.execute(
            select(Setting).where(Setting.key == 'chatterbox_base_url')
        )
        db_base_setting = db_base_result.scalars().first()
        if db_base_setting and db_base_setting.value:
            _add_candidate(db_base_setting.value)

        _add_candidate('http://chatterbox-shim:8000')

        chatterbox_status = 'unknown'
        chatterbox_detail: Optional[str] = None
        chatterbox_endpoint_used: Optional[str] = None

        if chatterbox_candidates:
            last_status = 'stopped'
            last_detail: str | None = None

            async with httpx.AsyncClient(timeout=5.0) as client:
                for base in chatterbox_candidates:
                    health_url = f"{base}/health"
                    try:
                        resp = await client.get(health_url)
                        if resp.status_code == 200:
                            chatterbox_status = 'running'
                            chatterbox_endpoint_used = base
                            try:
                                payload = resp.json()
                                if isinstance(payload, dict):
                                    summary = payload.get('detail') or payload.get('status') or payload.get('message')
                                    if isinstance(summary, str) and summary.strip():
                                        chatterbox_detail = summary.strip()
                            except Exception:
                                chatterbox_detail = None
                            if not chatterbox_detail:
                                chatterbox_detail = f"Healthy response from {base}"
                            break
                        else:
                            last_status = 'warning'
                            last_detail = f"HTTP {resp.status_code} from {health_url}"
                            chatterbox_endpoint_used = base
                    except Exception as exc:
                        last_status = 'stopped'
                        last_detail = f"{type(exc).__name__}: {exc}"[:200]
                        chatterbox_endpoint_used = base
                else:
                    chatterbox_status = last_status
                    chatterbox_detail = last_detail or 'Unable to reach Chatterbox service'
        else:
            chatterbox_status = 'unknown'
            chatterbox_detail = 'Chatterbox base URL not configured.'

        if chatterbox_detail and len(chatterbox_detail) > 200:
            chatterbox_detail = chatterbox_detail[:200]

        return {
            "status": "success",
            "statistics": {
                "total_24h": total_24h,
                "success_24h": success_24h,
                "failed_24h": failed_24h,
                "success_rate": round((success_24h / total_24h * 100) if total_24h > 0 else 0, 1),
                "avg_generation_time_ms": round(float(avg_gen_time), 1) if avg_gen_time else None,
                "avg_tts_time_ms": round(float(avg_tts_time), 1) if avg_tts_time else None
            },
            "recent_activity": recent_activity,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
                "has_more": offset + len(recent_activity) < total_count
            },
            "system_status": {
                "tts_service": "running",  # Could check actual service health
                "dj_worker": "running",    # Could check actual worker health
                "kokoro_tts": "running",   # Could check Kokoro health
                "chatterbox_tts": chatterbox_status
            },
            "chatterbox_health": {
                "status": chatterbox_status,
                "detail": chatterbox_detail,
                "endpoint": chatterbox_endpoint_used,
            }
        }
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.error("Failed to get TTS status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get TTS status: {str(e)}")

@router.get("/voices")
async def list_kokoro_voices():
    """List available Kokoro TTS voices via kokoro-tts service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.KOKORO_BASE_URL}/v1/audio/voices")
            if resp.status_code == 200:
                data = resp.json()
                voices = data.get("voices", data)
                # Normalize if array of dicts
                if isinstance(voices, list) and voices and isinstance(voices[0], dict):
                    names = []
                    for v in voices:
                        name = v.get("id") or v.get("name")
                        if name:
                            names.append(name)
                    voices = names
                return {"voices": voices}
    except Exception as e:
        logger = structlog.get_logger()
        logger.warning("Failed to list Kokoro voices", error=str(e))
    # Fallback small set
    fallback = [
        'af_bella','af_aria','af_sky','af_nicole',
        'am_onyx','am_michael','am_ryan','am_alex',
        'bf_ava','bf_sophie','bm_george','bm_james'
    ]
    return {"voices": fallback}

## XTTS voice listing removed (voice cloning not supported)

def _looks_like_audio(content: bytes, content_type: str | None) -> bool:
    try:
        if not content or len(content) < 1000:
            return False
        if content_type and content_type.startswith("audio/"):
            return True
        head = content[:4]
        if head.startswith(b"ID3"):
            return True
        if len(head) >= 2 and head[0] == 0xFF and head[1] in (0xFB, 0xF3, 0xF2):
            return True
        return False
    except Exception:
        return False


@router.post("/tts-test")
async def tts_test(payload: Dict[str, Any]):
    """Synthesize a short sample with Kokoro TTS and return an audio URL.

    Body fields:
    - text: sample text (optional; default provided)
    - voice: Kokoro voice id (fallback to defaults)
    - speed: float speed multiplier
    - volume: float volume multiplier
    """
    logger = structlog.get_logger()
    try:
        text = str(payload.get("text") or "This is a Raido DJ voice test.")
        voice = payload.get("voice") or payload.get("kokoro_voice") or "af_bella"
        try:
            speed = float(payload.get("speed") or payload.get("kokoro_speed") or 1.0)
        except Exception:
            speed = 1.0
        try:
            volume = float(payload.get("volume") or payload.get("dj_tts_volume") or 1.0)
        except Exception:
            volume = 1.0

        filename = f"tts_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path = f"/shared/tts/{filename}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.KOKORO_BASE_URL}/v1/audio/speech",
                json={
                    "input": text,
                    "voice": voice,
                    "model": "tts-1",
                    "response_format": "mp3",
                    "speed": speed,
                    "volume_multiplier": volume,
                },
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=f"Kokoro TTS error: {resp.text[:200]}")

            if not _looks_like_audio(resp.content, resp.headers.get("content-type")):
                detail = resp.text[:200] if resp.content else "no content"
                raise HTTPException(status_code=502, detail=f"Kokoro TTS returned non-audio response: {detail}")

        with open(out_path, "wb") as f:
            f.write(resp.content)

        url = f"/static/tts/{filename}"
        logger.info("TTS test synthesized", voice=voice, speed=speed, volume=volume, url=url)
        return {"status": "success", "audio_url": url, "voice": voice, "speed": speed, "volume": volume}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to synthesize TTS test", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to synthesize TTS test: {str(e)}")

## XTTS test endpoint removed (voice cloning not supported)

# Utility helpers -----------------------------------------------------------


GENERIC_VOICE_ALIASES: set[str] = {
    "", "voice", "voices", "default", "sample", "samples", "result", "results",
    "item", "items", "entry", "entries", "alias", "aliases", "name", "names",
    "label", "labels", "display_name", "title", "prompt", "prompts", "path",
    "paths", "file", "files", "file_path", "filepath", "filename", "file_name",
    "audio", "audio_prompt_path", "prompt_path", "audio_path",
    "manifest", "list", "lists", "speaker",
    "character", "model", "voice_id", "id", "uuid", "guid", "metadata",
    "meta", "data", "value", "key", "chatterbox", "voiceid", "version",
    "versions", "created_at", "updated_at", "timestamp", "timestamps",
}

NOISY_PREFIXES: tuple[str, ...] = (
    "commentary_",
    "tts_",
    "voice_",
    "audio_",
    "sample_",
)

UUIDISH_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

VOICE_STRING_FIELDS: tuple[str, ...] = (
    "id",
    "voice_id",
    "voice",
    "name",
    "label",
    "display_name",
    "title",
    "alias",
    "slug",
    "speaker",
    "character",
)

VOICE_PATH_FIELDS: tuple[str, ...] = (
    "audio_prompt_path",
    "file_path",
    "path",
    "sample_path",
    "voice_sample",
    "preview",
)


def _looks_like_uuidish(value: str) -> bool:
    if not value:
        return False
    cleaned = value.strip().lower()
    if not cleaned:
        return False
    if UUIDISH_RE.fullmatch(cleaned):
        return True
    # Accept UUIDs followed by suffixes (e.g. "<uuid>_alias")
    base = cleaned.split("_", 1)[0]
    if UUIDISH_RE.fullmatch(base):
        return True
    # Allow slightly non-standard UUID variants where hyphenated groups are still hex
    parts = cleaned.split("-")
    if len(parts) >= 5:
        base_parts = parts[:5]
        expected_lengths = (8, 4, 4, 4, 12)
        if all(len(part) == expected for part, expected in zip(base_parts, expected_lengths)):
            if all(part and all(char in "0123456789abcdef" for char in part) for part in base_parts):
                return True
    return False


def _is_noise_identifier(value: str) -> bool:
    if not value:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    if _looks_like_uuidish(stripped):
        return True
    lowered = stripped.lower()
    if lowered.startswith(NOISY_PREFIXES):
        return True
    # Detect UUID-prefixed filenames like "<uuid>_alias"
    prefix, _, _ = stripped.partition("_")
    if _looks_like_uuidish(prefix):
        return True
    lowered = stripped.lower()
    if "/" in stripped or "\\" in stripped:
        return True
    if lowered.endswith((".wav", ".mp3", ".ogg", ".flac", ".opus", ".m4a")):
        return True
    return False


def _extract_voice_names(payload: Any) -> list[str]:
    """Best-effort extraction of voice identifiers from arbitrary JSON payloads.

    Chatterbox installations return widely varying structures. We walk the response,
    collecting plausible identifiers while skipping generic metadata keys.

    Updated to prefer voice IDs and avoid duplicates/display names.
    """

    voices: list[str] = []
    seen: set[str] = set()

    def _append(value: Any, is_voice_id: bool = False) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        lowered = text.lower()
        if lowered in GENERIC_VOICE_ALIASES:
            return
        if "://" in text:
            return
        # Skip display names with parentheses like "Natalie (Custom)"
        if "(" in text and ")" in text:
            return

        # Only add the value if it's from a voice ID field or looks like a proper voice identifier
        # Skip extracting aliases from underscores/paths to avoid duplicates
        skip_original = lowered.startswith(NOISY_PREFIXES) or _is_noise_identifier(text)

        if lowered not in seen and not skip_original:
            seen.add(lowered)
            voices.append(text)

    def _walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            _append(node)
            return
        if isinstance(node, list):
            for item in node:
                _walk(item)
            return
        if isinstance(node, dict):
            # Only extract from voice ID fields, not paths or display names
            for field in ("id", "voice_id", "voice", "name"):
                if field in node and node.get(field):
                    _append(node.get(field), is_voice_id=True)
            # Recursively walk nested structures
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    _walk(value)

    _walk(payload)
    if not voices:
        return []

    friendly: list[str] = []
    friendly_seen: set[str] = set()
    noisy: list[str] = []
    noisy_seen: set[str] = set()

    for candidate in voices:
        if not candidate:
            continue
        trimmed = candidate.strip()
        if not trimmed:
            continue
        key = trimmed.lower()
        if key in friendly_seen or key in noisy_seen:
            continue
        if _is_noise_identifier(trimmed):
            noisy.append(trimmed)
            noisy_seen.add(key)
        else:
            friendly.append(trimmed)
            friendly_seen.add(key)

    if friendly:
        return friendly
    return noisy


@router.get("/voices-chatterbox")
async def list_chatterbox_voices(db: AsyncSession = Depends(get_db)):
    """List Chatterbox voices if the server exposes them; otherwise return a small default.

    Tries a few endpoints on the configured Chatterbox server:
    - GET `${CHATTERBOX_BASE_URL}/voices`
    - GET `${CHATTERBOX_BASE_URL}/v1/voices`
    - GET `${CHATTERBOX_BASE_URL}/v1/audio/voices`
    Expects either an array of names or an object with ids/names.
    """
    try:
        candidates = []
        # Check DB overrides first
        try:
            from app.models import Setting
            result = await db.execute(select(Setting).where(Setting.key.in_(["chatterbox_voices_url", "chatterbox_base_url"])) )
            rows = result.scalars().all()
            db_vals = {row.key: row.value for row in rows}
            if db_vals.get("chatterbox_voices_url"):
                candidates.append(db_vals["chatterbox_voices_url"].strip())
            if db_vals.get("chatterbox_base_url") and not getattr(settings, 'CHATTERBOX_BASE_URL', None):
                # Use DB base if env not set
                base = db_vals["chatterbox_base_url"].strip().rstrip('/')
                for path in ("/api/voices", "/voices", "/v1/voices", "/v1/audio/voices"):
                    candidates.append(f"{base}{path}")
        except Exception:
            pass
        # 1) Explicit voices URL if provided
        if getattr(settings, 'CHATTERBOX_VOICES_URL', None):
            candidates.append(settings.CHATTERBOX_VOICES_URL.strip())
        # 2) Derive from base URL
        base = getattr(settings, 'CHATTERBOX_BASE_URL', None)
        if base:
            base = base.rstrip('/')
            # Common endpoints
            for path in ("/api/voices", "/voices", "/v1/voices", "/v1/audio/voices"):
                candidates.append(f"{base}{path}")
        # 3) Try chatterbox-shim local proxy first (priority)
        if 'http://chatterbox-shim:8000/api/voices' not in candidates:
            candidates.insert(0, 'http://chatterbox-shim:8000/api/voices')
        # 4) User-provided known host (fallback for convenience)
        if 'http://192.168.1.170:8080/api/voices' not in candidates:
            candidates.append('http://192.168.1.170:8080/api/voices')

        async with httpx.AsyncClient(timeout=5.0) as client:
            for url in candidates:
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    extracted = _extract_voice_names(data)
                    if extracted:
                        return {"voices": extracted}
                except Exception:
                    continue
    except Exception:
        pass

    # Fallback basic list
    return {"voices": ["default", "female", "male", "narrator", "announcer", "newscaster"]}

@router.post("/upload-voice-reference")
async def upload_voice_reference(
    file: UploadFile = File(...),
    voice_name: str = Form(...)
):
    """Voice cloning is disabled."""
    raise HTTPException(status_code=410, detail="Voice cloning is disabled in this deployment")

@router.delete("/voice-reference/{voice_name}")
async def delete_voice_reference(voice_name: str):
    """Voice cloning is disabled."""
    raise HTTPException(status_code=410, detail="Voice cloning is disabled in this deployment")

@router.get("/voice-references")
async def list_voice_references():
    """Voice cloning is disabled."""
    return {"voices": []}


@router.post("/tts-test-chatterbox")
async def tts_test_chatterbox(payload: Dict[str, Any]):
    """Synthesize a short sample with Chatterbox TTS (no voice cloning)."""
    logger = structlog.get_logger()
    try:
        text = str(payload.get("text") or "This is a Raido Chatterbox TTS voice test.")
        voice = payload.get("voice") or "default"
        
        # Parse Chatterbox-specific parameters
        try:
            exaggeration = float(payload.get("exaggeration") or 1.0)
        except Exception:
            exaggeration = 1.0
        
        try:
            cfg_weight = float(payload.get("cfg_weight") or 0.5)
        except Exception:
            cfg_weight = 0.5
        
        # Validate Chatterbox is configured
        chatterbox_base = getattr(settings, 'CHATTERBOX_BASE_URL', None)
        if not chatterbox_base:
            raise HTTPException(status_code=503, detail="Chatterbox TTS server not configured")
        
        filename = f"chatterbox_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
        out_path = f"/shared/tts/{filename}"
        
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
        }
        
        logger.info("Sending Chatterbox TTS request", 
                   payload=payload,
                   endpoint=f"{chatterbox_base.rstrip('/')}/v1/audio/speech")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            base = chatterbox_base.rstrip('/')

            # 1) Try OpenAI-compatible POST /v1/audio/speech
            resp = None
            try:
                url = f"{base}/v1/audio/speech"
                data = {
                    'model': 'tts-1',
                    'input': text,
                    'response_format': 'mp3',
                    'exaggeration': str(exaggeration),
                    'cfg_weight': str(cfg_weight),
                }
                if voice and voice != 'default':
                    data['voice'] = voice

                attempt = await client.post(url, data=data)
                if attempt.status_code == 200 and attempt.content:
                    if _looks_like_audio(attempt.content, attempt.headers.get("content-type")):
                        resp = attempt
                    else:
                        logger.warning("Chatterbox /v1/audio/speech returned non-audio", preview=attempt.text[:200])
                else:
                    logger.warning("Chatterbox /v1/audio/speech failed", status=attempt.status_code, text=attempt.text[:200])
            except Exception as e:
                logger.warning("Chatterbox /v1/audio/speech error", error=str(e))

            # 2) Fallback to legacy GET /tts (optionally include provided server reference path)
            if resp is None:
                params = {
                    'text': text,
                    'exaggeration': str(exaggeration),
                    'cfg_weight': str(cfg_weight),
                }
                if voice:
                    params['voice'] = voice
                # Allow caller to provide a server-side reference file path
                ref_param = payload.get('audio_prompt_path')
                if isinstance(ref_param, str) and len(ref_param) > 0:
                    params['audio_prompt_path'] = ref_param
                resp = await client.get(f"{base}/tts", params=params)

            if resp is None or resp.status_code != 200:
                raise HTTPException(
                    status_code=(resp.status_code if resp is not None else 502),
                    detail=f"Chatterbox TTS error: {(resp.text[:200] if resp is not None else 'no response')}"
                )

            if not _looks_like_audio(resp.content, resp.headers.get("content-type")):
                detail = resp.text[:200] if resp.content else "no content"
                raise HTTPException(status_code=502, detail=f"Chatterbox TTS returned non-audio response: {detail}")

            # Write audio content to file
            with open(out_path, "wb") as f:
                f.write(resp.content)
        
        url = f"/static/tts/{filename}"
        logger.info("Chatterbox TTS test synthesized", 
                   voice=voice, 
                   exaggeration=exaggeration, 
                   cfg_weight=cfg_weight, 
                   url=url,
                   text_preview=text[:50])
        return {
            "status": "success", 
            "audio_url": url, 
            "voice": voice,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "provider": "chatterbox"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to synthesize Chatterbox TTS test", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to synthesize Chatterbox TTS test: {str(e)}")

@router.post("/tts-benchmark")
async def tts_benchmark(payload: Dict[str, Any]):
    """Benchmark TTS speed comparison between Kokoro and Chatterbox for DJ commentary.
    
    Body fields:
    - text: optional custom text (defaults to sample DJ commentary)
    - kokoro_voice: Kokoro voice to use
    - chatterbox_voice: Chatterbox voice to use
    - kokoro_speed: Kokoro speed multiplier
    - chatterbox_exaggeration: Chatterbox exaggeration
    - chatterbox_cfg_weight: Chatterbox cfg_weight
    """
    logger = structlog.get_logger()
    try:
        import asyncio
        import time
        
        # Get benchmark parameters
        text = str(payload.get("text") or "Coming up next, we've got The Beatles with Hey Jude from the White Album. This legendary track was recorded in 1968 and became one of their most beloved anthems. Let's dive in!")
        kokoro_voice = payload.get("kokoro_voice") or "af_bella"
        chatterbox_voice = payload.get("chatterbox_voice") or "alloy"
        
        try:
            kokoro_speed = float(payload.get("kokoro_speed") or 1.0)
        except Exception:
            kokoro_speed = 1.0
            
        try:
            chatterbox_exaggeration = float(payload.get("chatterbox_exaggeration") or 1.0)
        except Exception:
            chatterbox_exaggeration = 1.0
            
        try:
            chatterbox_cfg_weight = float(payload.get("chatterbox_cfg_weight") or 0.5)
        except Exception:
            chatterbox_cfg_weight = 0.5
        
        results = {}
        
        # Benchmark Kokoro TTS
        logger.info("Starting Kokoro TTS benchmark", voice=kokoro_voice, speed=kokoro_speed)
        kokoro_start = time.time()
        kokoro_success = False
        kokoro_error = None
        kokoro_url = None
        
        try:
            filename = f"benchmark_kokoro_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
            out_path = f"/shared/tts/{filename}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{settings.KOKORO_BASE_URL}/v1/audio/speech",
                    json={
                        "input": text,
                        "voice": kokoro_voice,
                        "model": "tts-1",
                        "response_format": "mp3",
                        "speed": kokoro_speed,
                        "volume_multiplier": 1.0,
                    },
                )
                if resp.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(resp.content)
                    kokoro_url = f"/static/tts/{filename}"
                    kokoro_success = True
                else:
                    kokoro_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    
        except Exception as e:
            kokoro_error = str(e)
            
        kokoro_time = time.time() - kokoro_start
        
        results["kokoro"] = {
            "success": kokoro_success,
            "time_seconds": round(kokoro_time, 3),
            "audio_url": kokoro_url,
            "error": kokoro_error,
            "voice": kokoro_voice,
            "speed": kokoro_speed
        }
        
        # Benchmark Chatterbox TTS
        logger.info("Starting Chatterbox TTS benchmark", voice=chatterbox_voice)
        chatterbox_start = time.time()
        chatterbox_success = False
        chatterbox_error = None
        chatterbox_url = None
        
        try:
            chatterbox_base = getattr(settings, 'CHATTERBOX_BASE_URL', None)
            if not chatterbox_base:
                chatterbox_error = "Chatterbox TTS not configured"
            else:
                filename = f"benchmark_chatterbox_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.mp3"
                out_path = f"/shared/tts/{filename}"
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(
                        f"{chatterbox_base.rstrip('/')}/tts",
                        params={"text": text},
                    )
                    if resp.status_code == 200:
                        with open(out_path, "wb") as f:
                            f.write(resp.content)
                        chatterbox_url = f"/static/tts/{filename}"
                        chatterbox_success = True
                    else:
                        chatterbox_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                        
        except Exception as e:
            chatterbox_error = str(e)
            
        chatterbox_time = time.time() - chatterbox_start
        
        results["chatterbox"] = {
            "success": chatterbox_success,
            "time_seconds": round(chatterbox_time, 3),
            "audio_url": chatterbox_url,
            "error": chatterbox_error,
            "voice": chatterbox_voice,
            "exaggeration": chatterbox_exaggeration,
            "cfg_weight": chatterbox_cfg_weight
        }
        
        # Calculate winner and summary
        winner = None
        if kokoro_success and chatterbox_success:
            winner = "kokoro" if kokoro_time < chatterbox_time else "chatterbox"
        elif kokoro_success:
            winner = "kokoro"
        elif chatterbox_success:
            winner = "chatterbox"
            
        logger.info("TTS benchmark completed", 
                   kokoro_time=kokoro_time,
                   chatterbox_time=chatterbox_time,
                   winner=winner)
        
        return {
            "status": "success",
            "text": text,
            "results": results,
            "winner": winner,
            "benchmarked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to run TTS benchmark", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to run TTS benchmark: {str(e)}")


@router.get("/analytics")
async def get_analytics(
    range: str = Query("7d", description="Time range: 1d, 7d, 30d, or all"),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics data for songs and TTS commentary."""
    logger = structlog.get_logger()
    
    try:
        # Calculate date range
        now = datetime.now(timezone.utc)
        if range == "1d":
            start_date = now - timedelta(days=1)
        elif range == "7d":
            start_date = now - timedelta(days=7)
        elif range == "30d":
            start_date = now - timedelta(days=30)
        else:  # "all"
            start_date = datetime.min.replace(tzinfo=timezone.utc)
            
        # Get song data with genre breakdown (eager load tracks to avoid async issues)
        # Filter to main station only — exclude christmas and other secondary stations
        play_query = select(Play).options(selectinload(Play.track)).where(
            Play.started_at >= start_date,
            Play.station_identifier == 'main'
        )
        play_result = await db.execute(play_query)
        plays = play_result.scalars().all()
        
        # Calculate genre statistics
        genre_counts = Counter()
        genre_durations = {}
        total_tracks = len(plays)
        
        for play in plays:
            # Get genre from track data or use 'Unknown'
            genre = 'Unknown'
            if hasattr(play, 'track') and play.track:
                genre = play.track.genre or 'Unknown'
                # Clean up genre string
                genre = str(genre).strip()
            
            genre_counts[genre] += 1
            
            # Track durations for averages
            if genre not in genre_durations:
                genre_durations[genre] = []
            if hasattr(play, 'track') and play.track and play.track.duration_sec:
                genre_durations[genre].append(play.track.duration_sec)
        
        # Create genre breakdown with percentages and durations
        genre_breakdown = []
        for genre, count in genre_counts.most_common():
            percentage = (count / total_tracks * 100) if total_tracks > 0 else 0
            durations = genre_durations.get(genre, [])
            avg_duration = sum(durations) / len(durations) if durations else 0
            total_duration = sum(durations)
            
            genre_breakdown.append({
                "genre": genre,
                "count": count,
                "percentage": round(percentage, 2),
                "total_duration": round(total_duration, 2),
                "avg_duration": round(avg_duration, 2)
            })
        
        # Get TTS commentary data for word cloud (main station only)
        commentary_query = select(Commentary).where(
            Commentary.created_at >= start_date,
            Commentary.transcript.isnot(None),
            func.lower(func.coalesce(
                Commentary.context_data.op('->>')('station'),
                Commentary.context_data.op('->>')('station_name'),
                'main'
            )) == 'main'
        )
        commentary_result = await db.execute(commentary_query)
        commentaries = commentary_result.scalars().all()
        
        # Extract words from TTS transcripts
        all_words = []
        for commentary in commentaries:
            if commentary.transcript:
                # Clean and tokenize the text
                text = re.sub(r'[^\w\s]', ' ', commentary.transcript.lower())
                words = text.split()
                # Filter out common stop words and short words
                stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'a', 'an', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
                filtered_words = [w for w in words if len(w) > 2 and w not in stop_words and w.isalpha()]
                all_words.extend(filtered_words)
        
        # Create word frequency data
        word_counts = Counter(all_words)
        word_cloud_data = [
            {"word": word, "count": count}
            for word, count in word_counts.most_common(100)  # Top 100 words
        ]
        
        logger.info("Analytics data generated", 
                   total_tracks=total_tracks,
                   genres=len(genre_breakdown),
                   commentaries=len(commentaries),
                   unique_words=len(word_counts))
        
        return {
            "genre_breakdown": genre_breakdown,
            "total_tracks": total_tracks,
            "word_cloud_data": word_cloud_data,
            "date_range": {
                "start": start_date.isoformat(),
                "end": now.isoformat()
            }
        }

    except Exception as e:
        logger.error("Failed to get analytics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@router.get("/ollama-models")
async def list_ollama_models():
    """List available Ollama models from the configured Ollama server"""
    logger = structlog.get_logger()
    try:
        ollama_base = getattr(settings, 'OLLAMA_BASE_URL', None)
        if not ollama_base:
            logger.warning("Ollama base URL not configured")
            return {"models": []}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ollama_base.rstrip('/')}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                # Extract just the model names
                model_names = []
                for model in models:
                    if isinstance(model, dict) and "name" in model:
                        model_names.append(model["name"])
                    elif isinstance(model, str):
                        model_names.append(model)

                logger.info("Ollama models fetched", count=len(model_names), models=model_names)
                return {"models": model_names}
            else:
                logger.warning("Failed to fetch Ollama models", status=resp.status_code, text=resp.text[:200])
                return {"models": []}

    except Exception as e:
        logger.warning("Failed to fetch Ollama models", error=str(e))
        return {"models": []}

@router.post("/clear-recent-commentary")
async def clear_recent_commentary(db: AsyncSession = Depends(get_db)):
    """Clear all recent commentary records to allow new TTS generation"""
    logger = structlog.get_logger()
    try:
        from sqlalchemy import delete

        # Delete all commentary records
        result = await db.execute(delete(Commentary))
        deleted_count = result.rowcount
        await db.commit()

        logger.info("Recent commentary cleared", deleted_count=deleted_count)

        return {
            "status": "success",
            "message": f"Cleared {deleted_count} commentary records",
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error("Failed to clear recent commentary", error=str(e))
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear recent commentary: {str(e)}")

@router.get("/stations")
async def list_stations(db: AsyncSession = Depends(get_db)):
    """List all configured stations"""
    logger = structlog.get_logger()
    try:
        from app.models import Station
        
        result = await db.execute(
            select(Station).order_by(Station.id)
        )
        stations = result.scalars().all()
        
        return [
            {
                "id": station.id,
                "identifier": station.identifier,
                "name": station.name,
                "description": station.description,
                "is_active": station.is_active,
                "created_at": station.created_at,
                "updated_at": station.updated_at
            }
            for station in stations
        ]
        
    except Exception as e:
        logger.error("Failed to list stations", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list stations: {str(e)}")
