"""Background Voicing Engine Worker.

Crawls the track library and pre-renders DJ scripts + TTS audio using:
  - Claude 3.5 Haiku (Anthropic) for script generation
  - Chatterbox TTS (via shim) or Kokoro for audio generation

Budget Guard:
  - Enforces daily_spend_limit_usd and total_project_limit_usd.
  - Supports dry_run_mode: calculates projected cost without calling APIs.
  - Rate-limits API calls to rate_limit_per_minute.
"""

import asyncio
import os
from datetime import date, datetime
from typing import Optional
import structlog
import httpx

from app.core.config import settings
from app.services.anthropic_client import AnthropicClient, estimate_dry_run_cost
from app.services.genre_personas import get_persona_for_genre
from app.services.tts_service import TTSService

logger = structlog.get_logger()

VOICING_AUDIO_DIR = "/shared/tts/voicing"
API_BASE = settings.API_BASE_URL


class VoicingWorker:
    """Pre-renders commentary scripts and TTS audio for all library tracks."""

    def __init__(self):
        self.running = False
        self._stop_event = asyncio.Event()
        self.tts_service: Optional[TTSService] = None
        self.anthropic: Optional[AnthropicClient] = None

    def _init_services(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", None)
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot start voicing worker")

        self.anthropic = AnthropicClient(api_key=api_key)
        self.tts_service = TTSService()
        os.makedirs(VOICING_AUDIO_DIR, exist_ok=True)

    async def run(self):
        """Main loop: poll config, process tracks, respect budget."""
        logger.info("Voicing worker starting")
        self._init_services()
        self.running = True

        while not self._stop_event.is_set():
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error("Voicing worker cycle error", error=str(e))

            # Wait before next cycle (check config every 30s)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass

        logger.info("Voicing worker stopped")

    async def stop(self):
        self.running = False
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Core processing cycle
    # ------------------------------------------------------------------

    async def _process_cycle(self):
        config = await self._fetch_config()
        if not config:
            return

        if not config.get("is_running"):
            return

        dry_run = config.get("dry_run_mode", False)
        daily_limit = config.get("daily_spend_limit_usd", 1.0)
        project_limit = config.get("total_project_limit_usd", 10.0)
        rate_limit = config.get("rate_limit_per_minute", 10)
        total_spent = config.get("total_spent_usd", 0.0)

        if dry_run:
            await self._run_dry_run()
            return

        # Check project-wide limit
        if total_spent >= project_limit:
            await self._pause_worker(f"Project limit reached (${total_spent:.4f} >= ${project_limit:.2f})")
            return

        # Check daily limit
        daily_spent = await self._get_today_spend()
        if daily_spent >= daily_limit:
            logger.info("Daily spend limit reached, sleeping until tomorrow",
                        daily_spent=daily_spent, limit=daily_limit)
            return

        # Fetch next unvoiced track
        track = await self._fetch_next_unvoiced_track(config.get("last_processed_track_id"))
        if not track:
            logger.info("All tracks voiced — voicing worker complete")
            await self._mark_worker_stopped()
            return

        await self._voice_track(track, config, daily_limit - daily_spent, rate_limit)

    async def _voice_track(self, track: dict, config: dict, remaining_daily: float, rate_limit: int):
        track_id = track["id"]
        genre = track.get("genre")
        persona_name, system_prompt = get_persona_for_genre(genre)

        logger.info("Voicing track", track_id=track_id,
                    title=track.get("title"), artist=track.get("artist"),
                    genre=genre, persona=persona_name)

        # Mark as generating
        await self._update_voicing_status(track_id, "generating")

        # --- Script generation via Anthropic ---
        result = await self.anthropic.generate_dj_script(
            track_info=track,
            system_prompt=system_prompt,
            max_tokens=120,
        )

        if result is None:
            await self._update_voicing_status(track_id, "failed", error="Anthropic API call failed")
            return

        script_text, input_tokens, output_tokens, cost_usd = result

        # Enforce remaining daily budget
        if cost_usd > remaining_daily:
            await self._update_voicing_status(track_id, "pending", error=None)
            await self._pause_worker(f"Daily budget would be exceeded by this track (cost=${cost_usd:.5f})")
            return

        # --- TTS audio generation ---
        job_id = f"voicing_{track_id}"
        dj_settings = {"dj_voice_provider": settings.DJ_VOICE_PROVIDER}
        audio_filename = await self.tts_service.generate_audio(
            text=script_text,
            job_id=job_id,
            dj_settings=dj_settings,
        )

        # Move audio to voicing subdirectory if generated in main tts dir
        if audio_filename:
            src = os.path.join(settings.TTS_CACHE_DIR, audio_filename)
            dst_dir = VOICING_AUDIO_DIR
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, audio_filename)
            if os.path.exists(src) and src != dst:
                os.rename(src, dst)

        # --- Store result via API ---
        await self._store_voicing_result(
            track_id=track_id,
            genre_persona=persona_name,
            script_text=script_text,
            audio_filename=audio_filename,
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            voice_provider=self.tts_service.last_voice_provider,
            voice_id=self.tts_service.last_voice_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            status="ready" if audio_filename else "ready_text_only",
        )

        # --- Update budget ---
        await self._record_spend(input_tokens, output_tokens, cost_usd)

        # --- Update worker progress ---
        await self._update_worker_progress(track_id, cost_usd)

        # --- Rate limiting ---
        delay = 60.0 / max(rate_limit, 1)
        await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # Dry-run mode
    # ------------------------------------------------------------------

    async def _run_dry_run(self):
        """Calculate projected cost for entire library without calling any paid API."""
        logger.info("Running voicing dry-run cost projection")

        total = await self._fetch_total_track_count()
        projected = estimate_dry_run_cost(total)

        logger.info("Dry-run projection complete",
                    total_tracks=total,
                    projected_cost_usd=f"${projected:.4f}")

        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{API_BASE}/api/v1/voicing/config",
                json={
                    "dry_run_projected_cost_usd": projected,
                    "total_tracks_estimated": total,
                    "is_running": False,
                },
            )

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    async def _fetch_config(self) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{API_BASE}/api/v1/voicing/config")
                if r.status_code == 200:
                    return r.json()
        except Exception as e:
            logger.warning("Failed to fetch voicing config", error=str(e))
        return None

    async def _fetch_next_unvoiced_track(self, last_track_id: Optional[int]) -> Optional[dict]:
        try:
            params = {"after_id": last_track_id} if last_track_id else {}
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{API_BASE}/api/v1/voicing/next-unvoiced", params=params)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return None
        except Exception as e:
            logger.warning("Failed to fetch next unvoiced track", error=str(e))
        return None

    async def _fetch_total_track_count(self) -> int:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{API_BASE}/api/v1/tracks/", params={"per_page": 1})
                total = int(r.headers.get("X-Total-Count", "0"))
                return total
        except Exception:
            return 0

    async def _update_voicing_status(self, track_id: int, status: str, error: Optional[str] = None):
        try:
            payload = {"status": status}
            if error is not None:
                payload["error_message"] = error
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{API_BASE}/api/v1/voicing/tracks/{track_id}",
                    json=payload,
                )
        except Exception as e:
            logger.warning("Failed to update voicing status", track_id=track_id, error=str(e))

    async def _store_voicing_result(self, track_id: int, **kwargs):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.put(
                    f"{API_BASE}/api/v1/voicing/tracks/{track_id}",
                    json=kwargs,
                )
        except Exception as e:
            logger.error("Failed to store voicing result", track_id=track_id, error=str(e))

    async def _record_spend(self, input_tokens: int, output_tokens: int, cost_usd: float):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{API_BASE}/api/v1/voicing/budget/record",
                    json={
                        "date": date.today().isoformat(),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": cost_usd,
                    },
                )
        except Exception as e:
            logger.warning("Failed to record spend", error=str(e))

    async def _update_worker_progress(self, last_track_id: int, cost_usd: float):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{API_BASE}/api/v1/voicing/progress",
                    json={"last_processed_track_id": last_track_id, "cost_usd": cost_usd},
                )
        except Exception as e:
            logger.warning("Failed to update worker progress", error=str(e))

    async def _get_today_spend(self) -> float:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"{API_BASE}/api/v1/voicing/budget/today",
                )
                if r.status_code == 200:
                    return r.json().get("total_cost_usd", 0.0)
        except Exception:
            pass
        return 0.0

    async def _pause_worker(self, reason: str):
        logger.warning("Voicing worker paused", reason=reason)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{API_BASE}/api/v1/voicing/config",
                    json={"is_running": False, "paused_reason": reason},
                )
        except Exception as e:
            logger.error("Failed to pause worker", error=str(e))

    async def _mark_worker_stopped(self):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{API_BASE}/api/v1/voicing/config",
                    json={"is_running": False, "paused_reason": "All tracks voiced"},
                )
        except Exception as e:
            logger.warning("Failed to mark worker stopped", error=str(e))
