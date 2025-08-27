from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.stream import StreamStatus

router = APIRouter()

@router.get("/status", response_model=StreamStatus)
async def get_stream_status(db: AsyncSession = Depends(get_db)):
    """Get current stream status"""
    # For now, return mock status
    # In a real implementation, this would query Icecast status
    return StreamStatus(
        is_live=True,
        listeners=0,
        uptime_seconds=3600,
        current_bitrate=128,
        mount_point="/raido.mp3"
    )