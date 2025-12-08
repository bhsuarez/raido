"""Shared test fixtures for API tests."""

import asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Disable .env loading for tests
_env_path = Path(".env")
_env_renamed = False
if _env_path.exists():
    _env_path.rename(".env.bak")
    _env_renamed = True

from app.main import app
from app.core.database import Base, get_db
from app.models import Track, Station, Play, Commentary, Setting, User

if _env_renamed:
    Path(".env.bak").rename(".env")


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def client(async_session) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """Create synchronous test client for simple tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def sample_track(async_session: AsyncSession) -> Track:
    """Create a sample track for testing."""
    track = Track(
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        file_path="/mnt/music/test.mp3",
        duration=180,
        file_size=3000000,
        format="mp3",
        bitrate=320000
    )
    async_session.add(track)
    await async_session.commit()
    await async_session.refresh(track)
    return track


@pytest.fixture
async def sample_station(async_session: AsyncSession) -> Station:
    """Create a sample station for testing."""
    station = Station(
        name="Test Station",
        description="A test radio station",
        is_active=True,
        stream_url="http://localhost:8000/test.mp3"
    )
    async_session.add(station)
    await async_session.commit()
    await async_session.refresh(station)
    return station


@pytest.fixture
async def sample_tracks(async_session: AsyncSession) -> list[Track]:
    """Create multiple sample tracks for testing."""
    tracks = [
        Track(
            title=f"Song {i}",
            artist=f"Artist {i}",
            album=f"Album {i % 3}",
            file_path=f"/mnt/music/song{i}.mp3",
            duration=180 + i * 10,
            file_size=3000000 + i * 100000,
            format="mp3",
            bitrate=320000
        )
        for i in range(1, 6)
    ]

    for track in tracks:
        async_session.add(track)

    await async_session.commit()

    for track in tracks:
        await async_session.refresh(track)

    return tracks


@pytest.fixture
async def sample_play(async_session: AsyncSession, sample_track: Track) -> Play:
    """Create a play entry for testing."""
    from datetime import datetime, timezone
    play = Play(
        track_id=sample_track.id,
        started_at=datetime.now(timezone.utc),
        liquidsoap_id="100"
    )
    async_session.add(play)
    await async_session.commit()
    await async_session.refresh(play)
    return play


@pytest.fixture
async def sample_settings(async_session: AsyncSession) -> Setting:
    """Create settings for testing."""
    settings = Setting(
        key="dj_provider",
        value="openai"
    )
    async_session.add(settings)
    await async_session.commit()
    await async_session.refresh(settings)
    return settings
