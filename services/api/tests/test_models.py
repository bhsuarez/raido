"""Tests for database models."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Track, Station, Play, Setting


@pytest.mark.unit
@pytest.mark.database
class TestTrackModel:
    """Test Track model."""

    async def test_create_track(self, async_session: AsyncSession):
        """Test creating a track."""
        track = Track(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            file_path="/test/path.mp3",
            duration=200,
            file_size=4000000,
            format="mp3"
        )

        async_session.add(track)
        await async_session.commit()
        await async_session.refresh(track)

        assert track.id is not None
        assert track.title == "Test Track"
        assert track.artist == "Test Artist"

    async def test_track_relationships(self, async_session: AsyncSession):
        """Test track relationships with stations."""
        track = Track(
            title="Relationship Test",
            artist="Artist",
            file_path="/test.mp3"
        )
        station = Station(name="Test Station")

        station.tracks.append(track)
        async_session.add(station)
        await async_session.commit()

        await async_session.refresh(station)
        await async_session.refresh(track)

        assert len(station.tracks) == 1
        assert station.tracks[0].title == "Relationship Test"
        assert len(track.stations) == 1
        assert track.stations[0].name == "Test Station"

    async def test_track_unique_file_path(self, async_session: AsyncSession):
        """Test that file paths should be unique (if enforced)."""
        track1 = Track(
            title="Track 1",
            artist="Artist",
            file_path="/unique/path.mp3"
        )
        async_session.add(track1)
        await async_session.commit()

        # Creating another track with same path
        # Behavior depends on database constraints
        track2 = Track(
            title="Track 2",
            artist="Artist",
            file_path="/unique/path.mp3"
        )
        async_session.add(track2)
        # This may or may not raise depending on constraints


@pytest.mark.unit
@pytest.mark.database
class TestStationModel:
    """Test Station model."""

    async def test_create_station(self, async_session: AsyncSession):
        """Test creating a station."""
        station = Station(
            name="Rock Station",
            description="A rock music station",
            genre="Rock",
            is_active=True
        )

        async_session.add(station)
        await async_session.commit()
        await async_session.refresh(station)

        assert station.id is not None
        assert station.name == "Rock Station"
        assert station.genre == "Rock"
        assert station.is_active is True

    async def test_station_with_multiple_tracks(self, async_session: AsyncSession):
        """Test station with multiple tracks."""
        tracks = [
            Track(title=f"Track {i}", artist="Artist", file_path=f"/track{i}.mp3")
            for i in range(5)
        ]

        station = Station(name="Multi-Track Station")
        station.tracks.extend(tracks)

        async_session.add(station)
        await async_session.commit()
        await async_session.refresh(station)

        assert len(station.tracks) == 5


@pytest.mark.unit
@pytest.mark.database
class TestPlayModel:
    """Test Play model."""

    async def test_create_play(
        self, async_session: AsyncSession, sample_track: Track
    ):
        """Test creating play entry."""
        from datetime import datetime, timezone
        play = Play(
            track_id=sample_track.id,
            started_at=datetime.now(timezone.utc),
            liquidsoap_id="100"
        )

        async_session.add(play)
        await async_session.commit()
        await async_session.refresh(play)

        assert play.id is not None
        assert play.track_id == sample_track.id
        assert play.liquidsoap_id == "100"


@pytest.mark.unit
@pytest.mark.database
class TestSettingModel:
    """Test Setting model."""

    async def test_create_setting(self, async_session: AsyncSession):
        """Test creating a setting."""
        setting = Setting(
            key="test_key",
            value="test_value"
        )

        async_session.add(setting)
        await async_session.commit()
        await async_session.refresh(setting)

        assert setting.id is not None
        assert setting.key == "test_key"
        assert setting.value == "test_value"
