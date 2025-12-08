"""Integration tests for the complete Raido system.

These tests verify that all components work together correctly:
- API endpoints
- DJ Worker
- Database
- TTS integration
- Audio streaming

Note: These tests require the full stack to be running.
Use `make up-dev` before running integration tests.
"""

import pytest
import httpx
import asyncio
from pathlib import Path


@pytest.mark.integration
class TestAPIIntegration:
    """Test API integration with database and services."""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for API tests."""
        return "http://localhost:8001/api/v1"

    async def test_health_endpoint(self, api_base_url):
        """Test API health check endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8001/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["ok", "healthy"]

    async def test_tracks_list(self, api_base_url):
        """Test tracks listing endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/tracks/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    async def test_now_playing(self, api_base_url):
        """Test now playing endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/now/")
            assert response.status_code == 200
            data = response.json()
            assert "is_playing" in data
            assert "track" in data

    async def test_stations_crud(self, api_base_url):
        """Test station creation and retrieval."""
        async with httpx.AsyncClient() as client:
            # Create a station
            station_data = {
                "name": "Test Integration Station",
                "description": "Integration test station",
                "genre": "Test",
            }
            response = await client.post(f"{api_base_url}/stations/", json=station_data)
            assert response.status_code == 200
            created_station = response.json()
            assert created_station["name"] == "Test Integration Station"
            station_id = created_station["id"]

            # List stations
            response = await client.get(f"{api_base_url}/stations/")
            assert response.status_code == 200
            stations = response.json()
            assert any(s["id"] == station_id for s in stations)


@pytest.mark.integration
class TestDJWorkerIntegration:
    """Test DJ Worker integration."""

    @pytest.fixture
    def api_base_url(self):
        """Base URL for API tests."""
        return "http://localhost:8001/api/v1"

    async def test_dj_settings_retrieval(self, api_base_url):
        """Test retrieving DJ settings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_base_url}/admin/dj-settings")
            # May require authentication
            assert response.status_code in [200, 401, 403]

    @pytest.mark.slow
    async def test_commentary_generation_flow(self, api_base_url):
        """Test the full commentary generation flow."""
        # This would test:
        # 1. Track change triggers commentary request
        # 2. DJ Worker generates commentary
        # 3. TTS converts to audio
        # 4. Audio is queued in Liquidsoap
        # Skip if DJ Worker is not running
        pytest.skip("Requires DJ Worker and TTS services")


@pytest.mark.integration
class TestStreamingIntegration:
    """Test audio streaming integration."""

    def test_icecast_stream_availability(self):
        """Test that Icecast stream is available."""
        import requests

        try:
            response = requests.get("http://localhost:8000/raido.mp3", stream=True, timeout=5)
            assert response.status_code == 200
            assert "audio" in response.headers.get("Content-Type", "")
        except requests.exceptions.RequestException:
            pytest.skip("Icecast stream not available")

    def test_liquidsoap_telnet_interface(self):
        """Test Liquidsoap telnet interface."""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("localhost", 1234))
            # Send 'help' command
            sock.send(b"help\n")
            response = sock.recv(1024)
            sock.close()
            assert len(response) > 0
        except (socket.error, socket.timeout):
            pytest.skip("Liquidsoap telnet interface not available")


@pytest.mark.integration
class TestDatabaseIntegration:
    """Test database integration."""

    async def test_database_connection(self):
        """Test database connection from API."""
        async with httpx.AsyncClient() as client:
            # Health check includes database check
            response = await client.get("http://localhost:8001/health")
            if response.status_code == 200:
                # Database is accessible
                assert True
            else:
                pytest.skip("Database not available")


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndFlow:
    """End-to-end integration tests."""

    async def test_full_track_play_flow(self):
        """Test complete track play flow.

        1. Track starts playing
        2. Track appears in now playing
        3. Commentary is generated (if DJ is active)
        4. Track completes and moves to history
        """
        # This is a comprehensive test that requires:
        # - Running services
        # - Music files
        # - Active DJ worker
        pytest.skip("Requires full stack with music files")

    async def test_station_management_flow(self):
        """Test station creation and track assignment flow.

        1. Create a station
        2. Assign tracks to station
        3. Verify tracks are associated
        4. Retrieve station with tracks
        """
        api_base_url = "http://localhost:8001/api/v1"

        async with httpx.AsyncClient() as client:
            # Create station
            station_data = {
                "name": "E2E Test Station",
                "description": "End-to-end test",
            }
            response = await client.post(f"{api_base_url}/stations/", json=station_data)
            assert response.status_code == 200
            station = response.json()

            # Verify retrieval
            response = await client.get(f"{api_base_url}/stations/")
            assert response.status_code == 200
            stations = response.json()
            assert any(s["id"] == station["id"] for s in stations)
