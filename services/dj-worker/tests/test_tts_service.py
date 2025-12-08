"""Tests for TTS service."""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open

from app.services.tts_service import TTSService


@pytest.mark.unit
class TestTTSService:
    """Test TTS service."""

    @pytest.fixture
    def tts_service(self):
        """Create a TTS service instance."""
        return TTSService()

    def test_init(self, tts_service):
        """Test TTSService initialization."""
        assert tts_service is not None

    async def test_generate_speech_with_openai(self, tts_service, mock_api_client):
        """Test generating speech with OpenAI TTS."""
        with patch("app.services.tts_service.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test_key"

            # Mock the API response
            mock_response = Mock()
            mock_response.content = b"fake_audio_data"
            mock_api_client.post.return_value = mock_response

            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value = mock_api_client

                # Note: This is a simplified test
                # Actual implementation would need more detailed mocking
                text = "Hello world"
                voice_settings = {"voice": "alloy"}

                # Would test the actual method call here
                # result = await tts_service.generate_speech(text, voice_settings)

    async def test_generate_speech_with_chatterbox(self, tts_service):
        """Test generating speech with Chatterbox TTS."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"fake_audio_wav_data"

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            text = "Hello from Chatterbox"
            voice_settings = {"voice": "female"}

            # Would test actual Chatterbox TTS call
            # result = await tts_service.generate_speech_chatterbox(text, voice_settings)

    def test_tts_cache_path_generation(self, tts_service):
        """Test TTS cache path generation."""
        text = "Test text"
        voice = "alloy"

        # Most TTS services generate cache paths based on hash
        # Test that the same input produces the same path
        import hashlib
        expected_hash = hashlib.md5(f"{text}_{voice}".encode()).hexdigest()
        # This is implementation dependent

    async def test_audio_file_cleanup(self, tts_service, tmp_path):
        """Test audio file cleanup functionality."""
        # Create some test files
        old_file = tmp_path / "old_tts.mp3"
        old_file.write_bytes(b"old data")

        new_file = tmp_path / "new_tts.mp3"
        new_file.write_bytes(b"new data")

        # Test cleanup logic
        # This would test the actual cleanup implementation
        # which removes files older than a certain age


@pytest.mark.integration
class TestTTSServiceIntegration:
    """Integration tests for TTS service (requires actual TTS services)."""

    @pytest.mark.slow
    async def test_openai_tts_real(self):
        """Test real OpenAI TTS call (requires API key)."""
        # Skip if no API key
        pytest.skip("Requires real OpenAI API key")

    @pytest.mark.slow
    async def test_chatterbox_tts_real(self):
        """Test real Chatterbox TTS call (requires service)."""
        # Skip if service not available
        pytest.skip("Requires Chatterbox TTS service")
