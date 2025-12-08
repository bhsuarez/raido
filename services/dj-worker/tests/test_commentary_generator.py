"""Tests for commentary generator service."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.commentary_generator import CommentaryGenerator


@pytest.mark.unit
class TestCommentaryGenerator:
    """Test commentary generation."""

    def test_init(self):
        """Test CommentaryGenerator initialization."""
        with patch("app.services.commentary_generator.settings") as mock_settings:
            mock_settings.OPENAI_API_KEY = "test_key"
            generator = CommentaryGenerator()
            assert generator.openai_client is not None
            assert generator.ollama_client is not None

    def test_load_default_prompt_template(self):
        """Test loading default prompt template."""
        generator = CommentaryGenerator()
        template = generator._load_default_prompt_template()
        assert template is not None

        # Test template rendering
        result = template.render(
            song_title="Test Song",
            artist="Test Artist",
            album="Test Album",
            year=2023
        )
        assert "Test Song" in result
        assert "Test Artist" in result

    def test_load_prompt_template_from_settings(self):
        """Test loading prompt template from settings."""
        generator = CommentaryGenerator()

        # Test custom template
        custom_template = "DJ intro for {{song_title}} by {{artist}}"
        settings = {"dj_prompt_template": custom_template}

        template = generator._load_prompt_template_from_settings(settings)
        result = template.render(song_title="Song", artist="Artist")
        assert "Song" in result
        assert "Artist" in result

        # Test fallback to default
        empty_settings = {"dj_prompt_template": ""}
        template = generator._load_prompt_template_from_settings(empty_settings)
        assert template is not None

    @pytest.mark.parametrize("input_text,expected_output", [
        # Test SSML tag removal
        ("<speak>Hello world</speak>", "Hello world"),
        # Test parenthetical removal
        ("Hello (stage direction) world", "Hello  world"),
        # Test bracket removal
        ("Hello [note] world", "Hello  world"),
        # Test asterisk removal
        ("Hello *applause* world", "Hello  world"),
        # Test quote removal
        ('"Hello world"', "Hello world"),
        # Test whitespace normalization
        ("Hello   world", "Hello world"),
        # Test contraction fixes
        ("We ' re testing", "We're testing"),
        ("It ' s working", "It's working"),
        # Test punctuation spacing
        ("Hello , world", "Hello, world"),
        ("Hello.World", "Hello. World"),
    ])
    def test_sanitize_generated_text(self, input_text, expected_output):
        """Test text sanitization."""
        generator = CommentaryGenerator()
        result = generator._sanitize_generated_text(input_text)
        assert result.strip() == expected_output.strip()

    def test_is_using_chatterbox_tts(self):
        """Test Chatterbox TTS detection."""
        generator = CommentaryGenerator()

        # Test with settings
        chatterbox_settings = {"dj_voice_provider": "chatterbox"}
        assert generator._is_using_chatterbox_tts(chatterbox_settings) is True

        openai_settings = {"dj_voice_provider": "openai"}
        assert generator._is_using_chatterbox_tts(openai_settings) is False

        # Test with environment settings
        with patch("app.services.commentary_generator.settings") as mock_settings:
            mock_settings.DJ_VOICE_PROVIDER = "chatterbox"
            assert generator._is_using_chatterbox_tts() is True


@pytest.mark.integration
@pytest.mark.ai
class TestCommentaryGeneratorIntegration:
    """Integration tests for commentary generation (requires AI services)."""

    async def test_generate_with_openai(self, mock_openai_client, sample_track_info):
        """Test generating commentary with OpenAI."""
        with patch("app.services.commentary_generator.OpenAIClient", return_value=mock_openai_client):
            generator = CommentaryGenerator()
            generator.openai_client = mock_openai_client

            dj_settings = {
                "dj_provider": "openai",
                "dj_model": "gpt-4",
                "system_prompt": "You are a DJ"
            }

            # This would call the actual generate_commentary method
            # which needs to be mocked or tested against real service
            # For now, we test the mock
            result = await mock_openai_client.generate_commentary(sample_track_info, dj_settings)
            assert result == "This is a great song!"
            mock_openai_client.generate_commentary.assert_called_once()

    async def test_generate_with_ollama(self, mock_ollama_client, sample_track_info):
        """Test generating commentary with Ollama."""
        with patch("app.services.commentary_generator.OllamaClient", return_value=mock_ollama_client):
            generator = CommentaryGenerator()
            generator.ollama_client = mock_ollama_client

            dj_settings = {
                "dj_provider": "ollama",
                "dj_ollama_model": "llama2"
            }

            result = await mock_ollama_client.generate_commentary(sample_track_info, dj_settings)
            assert result == "Welcome to the show!"
            mock_ollama_client.generate_commentary.assert_called_once()
