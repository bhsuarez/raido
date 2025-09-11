from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Track
from app.schemas import TrackRead

router = APIRouter()


@router.get("/", response_model=List[TrackRead])
async def list_tracks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Track))
    tracks = result.scalars().all()
    return tracks
