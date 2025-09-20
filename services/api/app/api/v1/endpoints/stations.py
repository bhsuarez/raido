"""Station management endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Station, Track
from app.schemas import StationCreate, StationRead

router = APIRouter()


@router.get("/", response_model=List[StationRead])
async def list_stations(db: AsyncSession = Depends(get_db)):
    """Return all stations with their associated tracks."""
    result = await db.execute(select(Station).options(selectinload(Station.tracks)))
    return result.scalars().unique().all()


@router.post("/", response_model=StationRead)
async def create_station(
    station: StationCreate, db: AsyncSession = Depends(get_db)
) -> Station:
    """Create a new station and attach any provided tracks."""
    db_station = Station(
        name=station.name,
        description=station.description,
        genre=station.genre,
        dj_persona=station.dj_persona,
        artwork_url=station.artwork_url,
    )

    if station.track_ids:
        result = await db.execute(select(Track).where(Track.id.in_(station.track_ids)))
        db_station.tracks = result.scalars().all()

    db.add(db_station)
    await db.commit()
    await db.refresh(db_station)
    return db_station
