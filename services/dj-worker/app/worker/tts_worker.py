"""TTS Worker — Converts ready_text_only voicing records to full audio.

Reads scripts from the voicing cache (status=ready_text_only) and generates
audio via Chatterbox TTS, upgrading records to status=ready.

Runs as a separate service (tts-worker) alongside the voicing-worker.
Loops forever — picks up newly scripted tracks automatically on each poll.
"""

import asyncio
import os
from typing import Optional
import structlog
import httpx

from app.core.config import settings
from app.services.tts_service import TTSService

logger = structlog.get_logger()

VOICING_AUDIO_DIR = "/shared/tts/voicing"
API_BASE = settings.API_BASE_URL


class TtsWorker:
    """Converts script-only voicing records into full TTS audio."""

    def __init__(self):
        self.running = False
        self._stop_event = asyncio.Event()
        self.tts_service: Optional[TTSService] = None

    def _init_services(self):
        self.tts_service = TTSService()
        os.makedirs(VOICING_AUDIO_DIR, exist_ok=True)

    async def run(self):
        """Main loop: poll for ready_text_only tracks, generate audio."""
        logger.info("TTS worker starting")
        self._init_services()
        self.running = True

        while not self._stop_event.is_set():
            try:
                await self._process_cycle()
            except Exception as e:
                logger.error("TTS worker cycle error", error=str(e))

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass

        logger.info("TTS worker stopped")

    async def stop(self):
        self.running = False
        self._stop_event.set()

    # ------------------------------------------------------------------
    # Core processing cycle
    # ------------------------------------------------------------------

    async def _process_cycle(self):
        config = await self._fetch_config()
        if not config:
            await asyncio.sleep(25)
            return

        if not config.get("tts_is_running"):
            await asyncio.sleep(25)
            return

        track = await self._fetch_next_pending_tts(config.get("tts_last_processed_track_id"))
        if not track:
            logger.info("No pending TTS tracks, polling for more")
            await asyncio.sleep(25)
            return

        await self._process_track(track)

    async def _process_track(self, track: dict):
        voicing_id = track["voicing_id"]
        track_id = track["track_id"]
        script_text = track.get("script_text", "")

        logger.info("TTS processing track", track_id=track_id,
                    title=track.get("title"), artist=track.get("artist"))

        audio_filename = await self.tts_service.generate_audio(
            text=script_text,
            job_id=f"tts_{track_id}",
            dj_settings={"dj_voice_provider": "chatterbox"},
        )

        # Move audio to voicing subdirectory if it landed in the main TTS dir
        if audio_filename:
            src = os.path.join(settings.TTS_CACHE_DIR, audio_filename)
            dst = os.path.join(VOICING_AUDIO_DIR, audio_filename)
            if os.path.exists(src) and src != dst:
                os.rename(src, dst)

        status = "ready" if audio_filename else "ready_text_only"
        await self._patch_voicing(
            track_id=track_id,
            audio_filename=audio_filename,
            status=status,
            voice_provider=self.tts_service.last_voice_provider,
        )

        if audio_filename:
            logger.info("TTS complete", track_id=track_id, status=status,
                        provider=self.tts_service.last_voice_provider)
        else:
            logger.warning("TTS failed, keeping ready_text_only", track_id=track_id)

        # Always advance checkpoint even on failure so we don't get stuck
        await self._update_tts_checkpoint(track_id)

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

    async def _fetch_next_pending_tts(self, last_track_id: Optional[int]) -> Optional[dict]:
        try:
            params = {"after_id": last_track_id} if last_track_id else {}
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{API_BASE}/api/v1/voicing/next-pending-tts", params=params)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    return None
        except Exception as e:
            logger.warning("Failed to fetch next pending TTS track", error=str(e))
        return None

    async def _patch_voicing(self, track_id: int, audio_filename: Optional[str],
                             status: str, voice_provider: Optional[str]):
        try:
            payload = {"status": status}
            if audio_filename is not None:
                payload["audio_filename"] = audio_filename
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{API_BASE}/api/v1/voicing/tracks/{track_id}",
                    json=payload,
                )
        except Exception as e:
            logger.warning("Failed to patch voicing record", track_id=track_id, error=str(e))

    async def _update_tts_checkpoint(self, track_id: int):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{API_BASE}/api/v1/voicing/progress",
                    json={"tts_last_processed_track_id": track_id},
                )
        except Exception as e:
            logger.warning("Failed to update TTS checkpoint", error=str(e))
