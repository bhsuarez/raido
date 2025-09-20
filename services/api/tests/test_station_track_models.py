from pathlib import Path
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# Temporarily disable loading the project's .env to avoid validation errors
_env_renamed = False
if Path(".env").exists():
    Path(".env").rename(".env.bak")
    _env_renamed = True

from app.core.database import Base  # noqa: E402
from app.models import Station, Track  # noqa: E402

if _env_renamed:
    Path(".env.bak").rename(".env")


def test_station_track_relationship():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            track = Track(title="Song", artist="Artist", file_path="/tmp/song.mp3")
            station = Station(name="Test Station")
            station.tracks.append(track)
            session.add(station)
            await session.commit()
            await session.refresh(station, attribute_names=["tracks"])
            await session.refresh(track, attribute_names=["stations"])

            assert station.tracks[0].title == "Song"
            assert track.stations[0].name == "Test Station"

    asyncio.run(_run())
