"""Tests for now playing API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.models import Track, Play


@pytest.mark.unit
class TestNowPlayingEndpoint:
    """Test now playing endpoint."""

    async def test_now_playing_no_tracks(self, client: AsyncClient):
        """Test now playing when no tracks are playing."""
        with patch("app.api.v1.endpoints.now_playing.LiquidsoapClient") as mock_client:
            # Mock Liquidsoap client to raise exception (not available)
            mock_client.return_value.list_request_ids.side_effect = Exception("Not available")

            response = await client.get("/api/v1/now-playing/")
            assert response.status_code == 200

            data = response.json()
            assert data["is_playing"] is False
            assert data["track"] is None

    async def test_now_playing_with_current_play(
        self, client: AsyncClient, async_session: AsyncSession, sample_track: Track
    ):
        """Test now playing with an active play."""
        # Create an active play (no ended_at)
        play = Play(
            track_id=sample_track.id,
            started_at=datetime.now(timezone.utc) - timedelta(seconds=30),
            ended_at=None,
            liquidsoap_id="1"
        )
        async_session.add(play)
        await async_session.commit()

        with patch("app.api.v1.endpoints.now_playing.LiquidsoapClient") as mock_client:
            mock_client.return_value.list_request_ids.side_effect = Exception("Not available")

            response = await client.get("/api/v1/now-playing/")
            assert response.status_code == 200

            data = response.json()
            assert data["is_playing"] is True
            assert data["track"] is not None
            assert data["track"]["title"] == "Test Song"
            assert data["track"]["artist"] == "Test Artist"

            # Check progress calculation
            if "progress" in data and data["progress"]:
                assert "elapsed_seconds" in data["progress"]
                assert "total_seconds" in data["progress"]
                assert "percentage" in data["progress"]


@pytest.mark.unit
class TestNextUpEndpoint:
    """Test next up endpoint."""

    async def test_next_up_fallback_random(
        self, client: AsyncClient, sample_tracks: list[Track]
    ):
        """Test next up falls back to random selection."""
        with patch("app.api.v1.endpoints.now_playing.LiquidsoapClient") as mock_client:
            # Mock empty Liquidsoap queue
            mock_client.return_value.list_request_ids.return_value = []

            response = await client.get("/api/v1/now-playing/next?limit=1")
            assert response.status_code == 200

            data = response.json()
            assert "next_tracks" in data
            assert isinstance(data["next_tracks"], list)

            if len(data["next_tracks"]) > 0:
                track = data["next_tracks"][0]["track"]
                assert "title" in track
                assert "artist" in track


@pytest.mark.unit
class TestPlayHistoryEndpoint:
    """Test play history endpoint."""

    async def test_history_empty(self, client: AsyncClient):
        """Test history when no plays exist."""
        response = await client.get("/api/v1/now-playing/history")
        assert response.status_code == 200

        data = response.json()
        assert "tracks" in data
        assert len(data["tracks"]) == 0

    async def test_history_with_completed_plays(
        self, client: AsyncClient, async_session: AsyncSession, sample_tracks: list[Track]
    ):
        """Test history returns completed plays."""
        # Create completed plays
        for i, track in enumerate(sample_tracks[:3]):
            play = Play(
                track_id=track.id,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=10 + i * 5),
                ended_at=datetime.now(timezone.utc) - timedelta(minutes=7 + i * 5),
                liquidsoap_id=str(i)
            )
            async_session.add(play)

        await async_session.commit()

        response = await client.get("/api/v1/now-playing/history?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert "tracks" in data
        assert len(data["tracks"]) == 3

        # Verify most recent is first
        tracks = data["tracks"]
        assert all("track" in item for item in tracks)
        assert all("play" in item for item in tracks)

    async def test_history_pagination(
        self, client: AsyncClient, async_session: AsyncSession, sample_tracks: list[Track]
    ):
        """Test history pagination."""
        # Create many plays
        for i in range(15):
            track = sample_tracks[i % len(sample_tracks)]
            play = Play(
                track_id=track.id,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=i * 5),
                ended_at=datetime.now(timezone.utc) - timedelta(minutes=i * 5 - 3),
                liquidsoap_id=str(i)
            )
            async_session.add(play)

        await async_session.commit()

        # Test first page
        response = await client.get("/api/v1/now-playing/history?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tracks"]) == 5

        # Test second page
        response = await client.get("/api/v1/now-playing/history?limit=5&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tracks"]) == 5
