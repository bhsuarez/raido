"""Anthropic Claude API client for the Voicing Engine.

Uses Claude 3.5 Haiku for cost-efficient, high-quality DJ script generation.
"""

import re
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger()

# Claude 3.5 Haiku pricing (USD per million tokens)
HAIKU_INPUT_COST_PER_M = 0.80
HAIKU_OUTPUT_COST_PER_M = 4.00
MODEL_ID = "claude-3-5-haiku-20241022"


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated USD cost for a Claude 3.5 Haiku API call."""
    return (
        input_tokens * HAIKU_INPUT_COST_PER_M / 1_000_000
        + output_tokens * HAIKU_OUTPUT_COST_PER_M / 1_000_000
    )


def estimate_dry_run_cost(num_tracks: int, avg_input_tokens: int = 250, avg_output_tokens: int = 80) -> float:
    """Project total cost for voicing an entire library without calling the API."""
    per_track = estimate_cost(avg_input_tokens, avg_output_tokens)
    return per_track * num_tracks


class AnthropicClient:
    """Thin async wrapper around the Anthropic Python SDK for DJ script generation."""

    def __init__(self, api_key: str):
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        except ImportError:
            raise RuntimeError(
                "anthropic package not installed. "
                "Add 'anthropic>=0.34.0' to dj-worker/requirements.txt"
            )

    async def generate_dj_script(
        self,
        track_info: dict,
        system_prompt: str,
        max_tokens: int = 120,
        temperature: float = 0.85,
    ) -> Optional[Tuple[str, int, int, float]]:
        """Generate a DJ script for the given track.

        Returns (script_text, input_tokens, output_tokens, cost_usd) or None on failure.
        """
        title = track_info.get("title", "Unknown Title")
        artist = track_info.get("artist", "Unknown Artist")
        album = track_info.get("album")
        year = track_info.get("year")
        genre = track_info.get("genre")

        user_prompt = self._build_user_prompt(title, artist, album, year, genre)

        try:
            response = await self._client.messages.create(
                model=MODEL_ID,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text if response.content else ""
            script = self._sanitize(raw_text)

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = estimate_cost(input_tokens, output_tokens)

            logger.info(
                "Anthropic script generated",
                track=f"{artist} - {title}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=f"${cost:.5f}",
            )
            return script, input_tokens, output_tokens, cost

        except Exception as e:
            logger.error("Anthropic API call failed", error=str(e), track=f"{artist} - {title}")
            return None

    def _build_user_prompt(
        self,
        title: str,
        artist: str,
        album: Optional[str],
        year: Optional[int],
        genre: Optional[str],
    ) -> str:
        parts = [f'Introduce the next track: "{title}" by {artist}']
        if album:
            parts.append(f'from the album "{album}"')
        if year:
            parts.append(f"({year})")
        if genre:
            parts.append(f"[Genre: {genre}]")
        parts.append(
            "\n\nWrite a 15-20 second DJ intro (spoken word). "
            "Include ONE interesting fact. No stage directions, no SSML tags, no quotes. "
            "End with a natural hand-off line like 'Here it is!' or 'Coming up next!'"
        )
        return " ".join(parts)

    @staticmethod
    def _sanitize(text: str) -> str:
        """Strip SSML, stage directions, and bracketed content."""
        if not text:
            return text
        cleaned = re.sub(r"<[^>]+>", "", text)
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
        cleaned = re.sub(r"\*[^*]+\*", "", cleaned)
        cleaned = cleaned.strip().strip('"\'')
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
