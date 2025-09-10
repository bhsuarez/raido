import asyncio

from app.services.commentary_generator import CommentaryGenerator


def test_sanitize_generated_text_strips_noise():
    gen = CommentaryGenerator()
    messy = "<speak>*applause*</speak> We <b> ' re </b> ready! (stage dir) [aside] Go !"
    cleaned = gen._sanitize_generated_text(messy)
    # Strips tags and bracketed parts, fixes tokenization spacing
    assert cleaned == "We're ready! Go!"


def test_estimate_token_cap_reasonable_bounds():
    gen = CommentaryGenerator()
    caps = [
        gen._estimate_token_cap({"dj_max_seconds": 0}),
        gen._estimate_token_cap({"dj_max_seconds": 10}),
        gen._estimate_token_cap({"dj_max_seconds": 60}),
    ]
    # Default, mid, upper bound clamped
    assert caps[0] == 200
    assert 40 <= caps[1] <= 300
    assert caps[2] <= 300


def test_trim_to_duration_ssml_and_punctuation():
    gen = CommentaryGenerator()
    dj_settings = {"dj_max_seconds": 5}
    long = (
        "<speak><break time=\"400ms\"/>" +
        " ".join(["word"] * 200) +
        "</speak>"
    )
    trimmed = gen._trim_to_duration(long, dj_settings)
    # Keeps SSML wrapper, ends on punctuation
    assert trimmed.startswith("<speak>") and trimmed.endswith("</speak>")
    assert any(trimmed.rstrip("</speak>").endswith(p) for p in (".", "!", "?"))


def test_build_prompt_context_fields_present():
    gen = CommentaryGenerator()
    track = {"title": "Song", "artist": "Artist", "album": "Album", "year": 2024, "duration_sec": 180}
    ctx = {"recent_history": ["A - 1", "B - 2"], "up_next": ["C - 3"]}
    out = gen._build_prompt_context(track, ctx, {"dj_commentary_interval": 2, "dj_tone": "calm"})
    assert out["song_title"] == "Song"
    assert out["artist"] == "Artist"
    assert out["album"] == "Album"
    assert out["year"] == 2024
    assert out["recent_history"] == "A - 1, B - 2"
    assert out["up_next"] == "C - 3"
    assert out["total_songs_in_block"] == 2
    assert out["tone"] == "calm"


async def _agen_templates(gen):
    ctx = {"artist": "X", "song_title": "Y"}
    result = await gen._generate_with_templates(ctx)
    assert result is not None
    assert "ssml" in result and result["ssml"].startswith("<speak>")
    assert "transcript_full" in result and "X" in result["transcript_full"]


def test_generate_with_templates_smoke():
    gen = CommentaryGenerator()
    asyncio.run(_agen_templates(gen))

