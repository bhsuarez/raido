"""Shared test fixtures for DJ Worker tests."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
import httpx


@pytest.fixture
def mock_api_client():
    """Create a mock API client."""
    client = Mock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.client = httpx.AsyncClient()
    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = Mock()
    client.generate_commentary = AsyncMock(return_value="This is a great song!")
    return client


@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = Mock()
    client.generate_commentary = AsyncMock(return_value="Welcome to the show!")
    return client


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    service = Mock()
    service.generate_speech = AsyncMock(return_value="/shared/tts/test.mp3")
    return service


@pytest.fixture
def sample_track_info():
    """Sample track information for testing."""
    return {
        "id": 1,
        "title": "Test Song",
        "artist": "Test Artist",
        "album": "Test Album",
        "year": 2023,
        "genre": "Rock",
        "duration_sec": 180
    }


@pytest.fixture
def sample_play_info():
    """Sample play information for testing."""
    return {
        "id": 1,
        "track_id": 1,
        "started_at": "2023-01-01T00:00:00Z",
        "liquidsoap_id": "100"
    }


@pytest.fixture
def sample_dj_settings():
    """Sample DJ settings for testing."""
    return {
        "provider": "openai",
        "voice_provider": "openai",
        "openai_model": "gpt-4",
        "openai_voice": "alloy",
        "system_prompt": "You are a radio DJ.",
        "is_active": True
    }


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_file = tmp_path / "test_audio.mp3"
    # Create a minimal MP3 file (just header bytes for testing)
    audio_file.write_bytes(b'\xff\xfb\x90\x00' + b'\x00' * 100)
    return str(audio_file)
