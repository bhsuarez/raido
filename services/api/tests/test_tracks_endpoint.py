"""Tests for tracks API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Track


@pytest.mark.unit
class TestTracksEndpoint:
    """Test tracks list endpoint."""

    async def test_list_tracks_empty(self, client: AsyncClient):
        """Test listing tracks when database is empty."""
        response = await client.get("/api/v1/tracks/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_tracks_with_data(self, client: AsyncClient, sample_tracks: list[Track]):
        """Test listing tracks returns all tracks."""
        response = await client.get("/api/v1/tracks/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 5
        assert all(track["title"].startswith("Song") for track in data)
        assert all(track["artist"].startswith("Artist") for track in data)

    async def test_track_response_structure(self, client: AsyncClient, sample_track: Track):
        """Test that track response has correct structure."""
        response = await client.get("/api/v1/tracks/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1

        track = data[0]
        assert "id" in track
        assert "title" in track
        assert "artist" in track
        assert "album" in track
        assert "file_path" in track
        assert "duration" in track or "duration_sec" in track

        assert track["title"] == "Test Song"
        assert track["artist"] == "Test Artist"
        assert track["album"] == "Test Album"
