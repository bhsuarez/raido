from pathlib import Path
from typing import List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Station, Track

logger = structlog.get_logger()

# Default station blueprints that should always exist in the database.
DEFAULT_STATIONS = [
    {
        "name": "Main Deck Radio",
        "slug": "main",
        "description": "24/7 mix of crew favourites and AI-curated adventures.",
        "genre": "Pirate Radio",
        "stream_mount": "/raido.mp3",
        "stream_name": "🏴‍☠️ Raido - Main Deck",
    },
    {
        "name": "North Pole Broadcast",
        "slug": "christmas",
        "description": "Holiday cheer direct from the crow's nest.",
        "genre": "Holiday",
        "stream_mount": "/raido-christmas.mp3",
        "stream_name": "🎄 Raido - Christmas Waves",
    },
]


def _build_playlist_directory() -> Path:
    """Ensure the shared station playlist directory exists."""
    base_dir = Path(settings.SHARED_DIR) / "stations"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def stream_proxy_path(stream_mount: str) -> str:
    """Return the proxy-relative stream path exposed by Caddy."""
    stream_mount = stream_mount if stream_mount.startswith("/") else f"/{stream_mount}"
    return f"/stream{stream_mount}"


async def ensure_default_stations(db: AsyncSession) -> List[Station]:
    """Create or update the built-in stations and attach basic metadata."""
    logger.info("Ensuring default radio stations are present")

    stations: List[Station] = []
    for blueprint in DEFAULT_STATIONS:
        result = await db.execute(select(Station).where(Station.slug == blueprint["slug"]))
        station = result.scalar_one_or_none()

        if station is None:
            station = Station(
                name=blueprint["name"],
                slug=blueprint["slug"],
                description=blueprint.get("description"),
                genre=blueprint.get("genre"),
                stream_mount=blueprint["stream_mount"],
                stream_name=blueprint.get("stream_name"),
            )
            db.add(station)
            logger.info("Created default station", slug=station.slug)
        else:
            station.name = blueprint["name"]
            station.description = blueprint.get("description")
            station.genre = blueprint.get("genre")
            station.stream_mount = blueprint["stream_mount"]
            station.stream_name = blueprint.get("stream_name")
            logger.info("Updated default station", slug=station.slug)

        stations.append(station)

    await db.flush()
    await assign_tracks_to_default_stations(db)
    await db.commit()

    # Refresh station data after commit so downstream callers have relationships.
    refreshed: List[Station] = []
    for station in stations:
        await db.refresh(station)
        refreshed.append(station)

    await rebuild_station_playlists(db)

    return refreshed


async def assign_tracks_to_default_stations(db: AsyncSession) -> None:
    """Attach tracks to the default stations based on classification flags."""
    result = await db.execute(
        select(Station).options(selectinload(Station.tracks)).where(
            Station.slug.in_([bp["slug"] for bp in DEFAULT_STATIONS])
        )
    )
    stations = {station.slug: station for station in result.scalars().unique()}

    # Query track sets used across stations.
    result = await db.execute(select(Track))
    all_tracks = result.scalars().all()

    result = await db.execute(select(Track).where(Track.is_christmas.is_(True)))
    christmas_tracks = result.scalars().all()

    if "main" in stations:
        stations["main"].tracks = list(all_tracks)
        logger.info("Assigned tracks to main station", track_count=len(stations["main"].tracks))

    if "christmas" in stations:
        stations["christmas"].tracks = list(christmas_tracks)
        logger.info(
            "Assigned tracks to christmas station",
            track_count=len(stations["christmas"].tracks),
        )


async def rebuild_station_playlists(db: AsyncSession) -> None:
    """Write playlist files on the shared volume for each station."""
    base_dir = _build_playlist_directory()

    result = await db.execute(select(Station).options(selectinload(Station.tracks)))
    stations = result.scalars().unique().all()

    for station in stations:
        playlist_path = base_dir / f"{station.slug}.m3u"
        try:
            with playlist_path.open("w", encoding="utf-8") as playlist_file:
                playlist_file.write("#EXTM3U\n")
                for track in station.tracks:
                    if track.file_path:
                        playlist_file.write(f"{track.file_path}\n")
            logger.info(
                "Wrote station playlist",
                station=station.slug,
                path=str(playlist_path),
                tracks=len(station.tracks),
            )
        except Exception as exc:
            logger.error(
                "Failed to write station playlist",
                station=station.slug,
                path=str(playlist_path),
                error=str(exc),
            )


async def station_stream_proxy_paths(db: AsyncSession) -> None:
    """Populate transient stream_url attributes for station Pydantic responses."""
    # This helper is intentionally left as a no-op placeholder. The actual stream URL is
    # constructed when serialising stations via schemas.
    return None
