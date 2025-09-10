from app.core.config import settings


def test_worker_defaults_safe():
    # Safer defaults after incident hardening
    assert settings.WORKER_POLL_INTERVAL == 10
    assert settings.MAX_CONCURRENT_JOBS == 1


def test_dj_defaults_provider_templates():
    # Prefer lightweight template generation by default
    assert settings.DJ_PROVIDER == "templates"
    assert settings.DJ_VOICE_PROVIDER in {"kokoro", "openai_tts", "xtts", "liquidsoap", "chatterbox"}

