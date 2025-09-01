from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timezone
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.schemas.admin import AdminSettingsResponse, AdminStatsResponse
from app.models import Commentary, Play, Setting
import httpx
try:
    from jinja2 import Template, TemplateSyntaxError
except Exception:
    Template = None  # type: ignore
    TemplateSyntaxError = Exception  # type: ignore

router = APIRouter()

@router.get("/settings", response_model=AdminSettingsResponse)
async def get_admin_settings(db: AsyncSession = Depends(get_db)):
    """Get admin settings"""
    try:
        logger = structlog.get_logger()
        
        # Get all settings from database
        result = await db.execute(select(Setting))
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
    db: AsyncSession = Depends(get_db)
):
    """Update admin settings"""
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
            # Check if setting exists
            result = await db.execute(select(Setting).where(Setting.key == key))
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
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(new_setting)
        
        await db.commit()
        logger.info("Settings updated", count=len(settings))
        
        return {"status": "success", "message": f"Updated {len(settings)} settings"}
        
    except Exception as e:
        logger.error("Failed to update settings", error=str(e))
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
        
        # Create commentary record
        commentary = Commentary(
            play_id=play_id,
            text=commentary_data.get("text", ""),
            transcript=commentary_data.get("transcript"),
            audio_url=audio_url,
            provider=commentary_data.get("provider", "openai"),
            model=commentary_data.get("model"),
            voice_provider=commentary_data.get("voice_provider", "openai"),
            voice_id=commentary_data.get("voice_id"),
            duration_ms=commentary_data.get("duration_ms"),
            generation_time_ms=commentary_data.get("generation_time_ms"),
            tts_time_ms=commentary_data.get("tts_time_ms"),
            status="ready",
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
            "audio_url": commentary.audio_url
        }
        
    except Exception as e:
        logger = structlog.get_logger()
        logger.error("Failed to create commentary", error=str(e), data=commentary_data)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create commentary: {str(e)}")

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
    limit: int = Query(10, ge=1, le=500)
):
    """Get TTS generation status and statistics"""
    try:
        logger = structlog.get_logger()
        
        # Get recent commentary records with generation stats
        from sqlalchemy import func, desc
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        window_start = now - timedelta(hours=window_hours)
        
        # Count total commentary in last 24h
        total_result = await db.execute(
            select(func.count(Commentary.id))
            .where(Commentary.created_at >= last_24h)
        )
        total_24h = total_result.scalar() or 0
        
        # Count successful commentary in last 24h
        success_result = await db.execute(
            select(func.count(Commentary.id))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.status == "ready")
        )
        success_24h = success_result.scalar() or 0
        
        # Count failed commentary in last 24h
        failed_result = await db.execute(
            select(func.count(Commentary.id))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.status == "failed")
        )
        failed_24h = failed_result.scalar() or 0
        
        # Get recent activity (last hour)
        recent_result = await db.execute(
            select(Commentary)
            .where(Commentary.created_at >= window_start)
            .order_by(desc(Commentary.created_at))
            .limit(limit)
        )
        recent_commentary = recent_result.scalars().all()
        
        # Get average generation times
        avg_gen_time_result = await db.execute(
            select(func.avg(Commentary.generation_time_ms))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.generation_time_ms.is_not(None))
        )
        avg_gen_time = avg_gen_time_result.scalar() or 0
        
        avg_tts_time_result = await db.execute(
            select(func.avg(Commentary.tts_time_ms))
            .where(Commentary.created_at >= last_24h)
            .where(Commentary.tts_time_ms.is_not(None))
        )
        avg_tts_time = avg_tts_time_result.scalar() or 0
        
        # Format recent activity (return full text; UI can decide how to render)
        recent_activity = []
        for comment in recent_commentary:
            recent_activity.append({
                "id": comment.id,
                "text": comment.text,  # may contain SSML
                "transcript": comment.transcript,  # full plain-text transcript when available
                "status": comment.status,
                "provider": comment.provider,
                "voice_provider": comment.voice_provider,
                "voice_id": comment.voice_id,
                "generation_time_ms": comment.generation_time_ms,
                "tts_time_ms": comment.tts_time_ms,
                "created_at": comment.created_at,
                "audio_url": comment.audio_url
            })
        
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
            "system_status": {
                "tts_service": "running",  # Could check actual service health
                "dj_worker": "running",    # Could check actual worker health
                "kokoro_tts": "running"    # Could check Kokoro health
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
        async with httpx.AsyncClient(timeout=5.0) as client:
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

@router.get("/voices-xtts")
async def list_xtts_voices():
    """List available XTTS voices via OpenTTS-compatible server.

    Tries `${XTTS_BASE_URL}/api/voices` and normalizes to a simple string list.
    """
    try:
        base = (settings.XTTS_BASE_URL or '').rstrip('/')
        if not base:
            # No XTTS configured; return empty list
            return {"voices": []}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/voices")
            if resp.status_code == 200:
                data = resp.json()
                voices = []
                # OpenTTS returns a dict of voices with details; collect keys/ids/names
                if isinstance(data, dict):
                    for k, v in data.items():
                        # Prefer the fully-qualified key (engine:id) so requests work reliably
                        key_name = str(k)
                        if key_name:
                            voices.append(key_name)
                elif isinstance(data, list):
                    for v in data:
                        if isinstance(v, dict):
                            # Fall back to id/name if only a list is provided
                            name = v.get('id') or v.get('name')
                            if name:
                                voices.append(str(name))
                        else:
                            voices.append(str(v))
                # De-duplicate while preserving order
                seen = set()
                ordered = []
                for v in voices:
                    if v not in seen:
                        seen.add(v)
                        ordered.append(v)
                # Also return the raw map so clients can discover speakers, etc.
                return {"voices": ordered, "voices_map": data}
    except Exception as e:
        logger = structlog.get_logger()
        logger.warning("Failed to list XTTS voices", error=str(e))
    return {"voices": [], "voices_map": {}}

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

@router.post("/tts-test-xtts")
async def tts_test_xtts(payload: Dict[str, Any]):
    """Synthesize a short sample with XTTS and return an audio URL.

    Body fields:
    - text: sample text (optional; default provided)
    - voice: XTTS voice id (e.g., 'coqui-tts:en_ljspeech')
    - speaker: speaker id for multi-speaker voices (optional)
    """
    logger = structlog.get_logger()
    try:
        text = str(payload.get("text") or "This is a Raido XTTS voice test.")
        voice = payload.get("voice") or "coqui-tts:en_ljspeech"
        speaker = payload.get("speaker") or None
        
        # Validate XTTS is configured
        xtts_base = getattr(settings, 'XTTS_BASE_URL', None)
        if not xtts_base:
            raise HTTPException(status_code=503, detail="XTTS server not configured")
        
        filename = f"xtts_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.wav"
        out_path = f"/shared/tts/{filename}"
        
        # Prepare XTTS request - use OpenTTS API format
        params = {
            'text': text,
            'voice': voice
        }
        if speaker:
            params['speaker'] = speaker
            
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Try OpenTTS format first: GET /api/tts with query params
            resp = await client.get(
                f"{xtts_base.rstrip('/')}/api/tts",
                params=params
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code, 
                    detail=f"XTTS error: {resp.text[:200]}"
                )
            
            # Write audio content to file
            with open(out_path, "wb") as f:
                f.write(resp.content)
        
        url = f"/static/tts/{filename}"
        logger.info("XTTS test synthesized", voice=voice, speaker=speaker, url=url)
        return {
            "status": "success", 
            "audio_url": url, 
            "voice": voice, 
            "speaker": speaker,
            "provider": "xtts"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to synthesize XTTS test", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to synthesize XTTS test: {str(e)}")

@router.get("/voices-chatterbox")
async def list_chatterbox_voices():
    """List available Chatterbox TTS voices."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to get voices from Chatterbox API
            chatterbox_base = getattr(settings, 'CHATTERBOX_BASE_URL', None)
            if not chatterbox_base:
                return {"voices": []}
            
            resp = await client.get(f"{chatterbox_base.rstrip('/')}/v1/voices")
            if resp.status_code == 200:
                data = resp.json()
                voices = data.get("data", [])
                # Extract voice names/IDs
                voice_list = []
                for voice in voices:
                    if isinstance(voice, dict):
                        voice_id = voice.get("id") or voice.get("name")
                        if voice_id:
                            voice_list.append(voice_id)
                    else:
                        voice_list.append(str(voice))
                return {"voices": voice_list}
    except Exception as e:
        logger = structlog.get_logger()
        logger.warning("Failed to list Chatterbox voices", error=str(e))
    
    # Fallback to common Chatterbox voices
    fallback = [
        "default", "alloy", "echo", "fable", "onyx", "nova", "shimmer"
    ]
    return {"voices": fallback}

@router.post("/tts-test-chatterbox")
async def tts_test_chatterbox(payload: Dict[str, Any]):
    """Synthesize a short sample with Chatterbox TTS and return an audio URL.

    Body fields:
    - text: sample text (optional; default provided)
    - voice: Chatterbox voice id (e.g., 'alloy', 'nova', 'onyx')
    - exaggeration: emotion intensity (0.25-2.0, default 1.0)
    - cfg_weight: pace control (0.0-1.0, default 0.5)
    """
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
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Use OpenAI-compatible endpoint
            resp = await client.post(
                f"{chatterbox_base.rstrip('/')}/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "response_format": "mp3",
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight,
                },
            )
            
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code, 
                    detail=f"Chatterbox TTS error: {resp.text[:200]}"
                )
            
            # Write audio content to file
            with open(out_path, "wb") as f:
                f.write(resp.content)
        
        url = f"/static/tts/{filename}"
        logger.info("Chatterbox TTS test synthesized", 
                   voice=voice, 
                   exaggeration=exaggeration, 
                   cfg_weight=cfg_weight, 
                   url=url)
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
