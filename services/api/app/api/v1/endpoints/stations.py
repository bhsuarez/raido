"""Station management endpoints."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models import Station, Track
from app.schemas import StationCreate, StationRead
from app.services.station_manager import rebuild_station_playlists, stream_proxy_path

router = APIRouter()


@router.get("/", response_model=List[StationRead])
async def list_stations(db: AsyncSession = Depends(get_db)):
    """Return all stations with their associated tracks."""
    result = await db.execute(select(Station).options(selectinload(Station.tracks)))
    stations = result.scalars().unique().all()
    for station in stations:
        station.stream_url = stream_proxy_path(station.stream_mount)
    return stations


@router.post("/", response_model=StationRead)
async def create_station(
    station: StationCreate, db: AsyncSession = Depends(get_db)
) -> Station:
    """Create a new station and attach any provided tracks."""
    db_station = Station(
        name=station.name,
        slug=station.slug,
        description=station.description,
        genre=station.genre,
        dj_persona=station.dj_persona,
        artwork_url=station.artwork_url,
        stream_mount=station.stream_mount,
        stream_name=station.stream_name,
    )

    if station.track_ids:
        result = await db.execute(select(Track).where(Track.id.in_(station.track_ids)))
        db_station.tracks = result.scalars().all()

    db.add(db_station)
    await db.commit()
    await rebuild_station_playlists(db)
    await db.refresh(db_station)
    db_station.stream_url = stream_proxy_path(db_station.stream_mount)
    return db_station
