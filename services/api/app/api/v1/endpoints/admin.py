from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timezone
import structlog

from app.core.database import get_db
from app.schemas.admin import AdminSettingsResponse, AdminStatsResponse
from app.models import Commentary, Play, Setting
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

@router.get("/tts-status")
async def get_tts_status(db: AsyncSession = Depends(get_db)):
    """Get TTS generation status and statistics"""
    try:
        logger = structlog.get_logger()
        
        # Get recent commentary records with generation stats
        from sqlalchemy import func, desc
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
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
            .where(Commentary.created_at >= last_hour)
            .order_by(desc(Commentary.created_at))
            .limit(10)
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
