"""Tests for stations API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Station, Track


@pytest.mark.unit
class TestStationsEndpoint:
    """Test stations API endpoints."""

    async def test_list_stations_empty(self, client: AsyncClient):
        """Test listing stations when database is empty."""
        response = await client.get("/api/v1/stations/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_stations_with_data(self, client: AsyncClient, sample_station: Station):
        """Test listing stations returns all stations."""
        response = await client.get("/api/v1/stations/")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Station"
        assert data[0]["description"] == "A test radio station"

    async def test_create_station_without_tracks(self, client: AsyncClient):
        """Test creating a station without tracks."""
        station_data = {
            "name": "New Station",
            "description": "A new test station",
            "genre": "Rock",
            "dj_persona": "Energetic DJ"
        }

        response = await client.post("/api/v1/stations/", json=station_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "New Station"
        assert data["description"] == "A new test station"
        assert data["genre"] == "Rock"
        assert data["dj_persona"] == "Energetic DJ"
        assert "id" in data

    async def test_create_station_with_tracks(
        self, client: AsyncClient, sample_tracks: list[Track]
    ):
        """Test creating a station with associated tracks."""
        track_ids = [track.id for track in sample_tracks[:3]]

        station_data = {
            "name": "Station with Tracks",
            "description": "A station with tracks",
            "track_ids": track_ids
        }

        response = await client.post("/api/v1/stations/", json=station_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Station with Tracks"
        assert "tracks" in data
        # Note: The actual structure depends on how the schema serializes tracks

    async def test_station_response_structure(self, client: AsyncClient, sample_station: Station):
        """Test that station response has correct structure."""
        response = await client.get("/api/v1/stations/")
        assert response.status_code == 200

        data = response.json()
        station = data[0]

        assert "id" in station
        assert "name" in station
        assert "description" in station
        assert "tracks" in station
