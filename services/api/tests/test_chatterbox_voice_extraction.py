import os

_EXTRA_ENV_KEYS = [
    "POSTGRES_PASSWORD",
    "XTTS_BASE_URL",
    "XTTS_VOICE",
    "KOKORO_VOICE",
    "KOKORO_SPEED",
    "CHATTERBOX_AUDIO_PROMPT_PATH",
]

for _key in _EXTRA_ENV_KEYS:
    os.environ.pop(_key, None)

from app.api.v1.endpoints import admin


def lower_set(values: list[str]) -> set[str]:
    return {value.lower() for value in values}


def test_extract_voice_names_from_simple_list():
    payload = {"voices": ["natalie", "brian", "default"]}

    result = admin._extract_voice_names(payload)  # type: ignore[attr-defined]
    names = lower_set(result)

    assert {"natalie", "brian"}.issubset(names)
    assert "default" not in names


def test_extract_voice_names_from_nested_results_structure():
    payload = {
        "voices": {
            "results": [
                {
                    "id": "abc123",
                    "name": "Captain Morgan",
                    "audio_prompt_path": "/shared/tts/captain_morgan.wav",
                },
                {
                    "voice_id": "legends_announcer",
                    "display_name": "Legends Announcer",
                    "file_path": "voices/legends_announcer.wav",
                },
            ],
            "default": "abc123",
        },
        "meta": {"version": 1},
    }

    result = admin._extract_voice_names(payload)  # type: ignore[attr-defined]
    names = lower_set(result)

    assert "abc123" in names
    assert any(candidate in names for candidate in {"captain morgan", "morgan"})
    assert "legends_announcer" in names
    assert "results" not in names
    assert "default" not in names


def test_extract_voice_names_handles_mapping_values():
    payload = {
        "voices": {
            "pirate_1": {
                "label": "Pirate One",
                "audio_prompt_path": "/shared/prompts/pirate_1.wav",
            },
            "narrator": "The Narrator",
        },
        "meta": {"version": 2},
    }

    result = admin._extract_voice_names(payload)  # type: ignore[attr-defined]
    names = lower_set(result)

    assert "pirate_1" in names
    assert "pirate one" in names
    assert "narrator" in names
    assert "the narrator" in names
    assert all(meta_key not in names for meta_key in {"version", "2"})


def test_extract_voice_names_filters_uuid_when_alias_available():
    payload = {
        "voices": [
            {
                "id": "cb231744-e7c6-4f56-9aaa-593720b38928",
                "name": "Natalie",
                "audio_prompt_path": "/shared/tts/cb231744-e7c6-4f56-9aaa-593720b38928_natalie.wav",
            }
        ]
    }

    result = admin._extract_voice_names(payload)  # type: ignore[attr-defined]
    names = lower_set(result)

    assert "natalie" in names
    assert all("cb231744" not in candidate for candidate in names)


def test_extract_voice_names_keeps_uuid_when_no_alias():
    payload = {
        "voices": [
            {
                "id": "d92260ce-6412-48d9-b348-d1d0706f4fbf",
            }
        ]
    }

    result = admin._extract_voice_names(payload)  # type: ignore[attr-defined]

    assert result
    assert any("d92260ce-6412-48d9-b348-d1d0706f4fbf" in candidate for candidate in result)
