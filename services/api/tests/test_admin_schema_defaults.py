from app.schemas.admin import AdminSettingsResponse


def test_admin_settings_defaults():
    s = AdminSettingsResponse()
    # Safer commentary defaults
    assert s.dj_provider == "templates"
    assert s.dj_voice_provider in {"openai_tts", "kokoro", "liquidsoap", "xtts", "chatterbox"}
    assert s.dj_commentary_interval == 1
    assert s.dj_max_seconds == 30
    assert s.dj_temperature == 0.8
    assert s.dj_max_tokens == 200

