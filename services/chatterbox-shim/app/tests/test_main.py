import asyncio
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import main


class VoiceRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._map_snapshot = dict(main.VOICE_FILE_MAP)

    def tearDown(self) -> None:
        main.VOICE_FILE_MAP.clear()
        main.VOICE_FILE_MAP.update(self._map_snapshot)

    def test_register_and_resolve_voice_reference(self) -> None:
        main.VOICE_FILE_MAP.clear()
        sample_path = "/tmp/test_voice.wav"
        main.register_voice_reference(
            voice_id="VOICE-123",
            voice_name="DJ-Test",
            audio_prompt_path=sample_path,
        )

        self.assertEqual(main.resolve_audio_prompt("voice-123"), sample_path)
        self.assertEqual(main.resolve_audio_prompt("dj-test"), sample_path)

    def test_resolve_fallback_voice_seeded_on_import(self) -> None:
        self.assertIsNotNone(main.resolve_audio_prompt("brian"))


class AttachAudioPromptTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._map_snapshot = dict(main.VOICE_FILE_MAP)
        self._refresh_snapshot = dict(main.VOICE_REFRESH_STATE)

    async def asyncTearDown(self) -> None:
        main.VOICE_FILE_MAP.clear()
        main.VOICE_FILE_MAP.update(self._map_snapshot)
        main.VOICE_REFRESH_STATE.update(self._refresh_snapshot)

    async def test_attach_audio_prompt_uses_existing_mapping(self) -> None:
        sample_path = "/tmp/attached.wav"
        main.VOICE_FILE_MAP.clear()
        main.VOICE_FILE_MAP["attached-voice"] = sample_path

        payload = {}
        await main._attach_audio_prompt(payload, "Attached-Voice")
        self.assertEqual(payload["audio_prompt_path"], sample_path)

    async def test_attach_audio_prompt_refreshes_registry_when_missing(self) -> None:
        main.VOICE_FILE_MAP.clear()

        async def fake_prime(log, force: bool = False):
            main.VOICE_FILE_MAP["dynamic"] = "/tmp/dynamic.wav"

        with patch.object(main, "_prime_voice_registry", new=AsyncMock(side_effect=fake_prime)) as mock_prime:
            payload: dict[str, str] = {}
            await main._attach_audio_prompt(payload, "dynamic")

        mock_prime.assert_awaited()
        self.assertEqual(payload["audio_prompt_path"], "/tmp/dynamic.wav")

    async def test_attach_audio_prompt_handles_voice_alias_suffix(self) -> None:
        main.VOICE_FILE_MAP.clear()
        main.register_voice_reference(voice_name="natalie", audio_prompt_path="/tmp/natalie.wav")

        payload: dict[str, str] = {}
        await main._attach_audio_prompt(payload, "cb231744-nat_natalie")
        self.assertEqual(payload["audio_prompt_path"], "/tmp/natalie.wav")

    async def test_attach_audio_prompt_syncs_local_sources(self) -> None:
        main.VOICE_FILE_MAP.clear()
        main.VOICE_FILE_MAP["present"] = "/tmp/present.wav"

        payload: dict[str, str] = {}
        with patch.object(main, "sync_local_voice_references") as sync_local:
            await main._attach_audio_prompt(payload, "present")

        sync_local.assert_called_once()
        self.assertEqual(payload["audio_prompt_path"], "/tmp/present.wav")


class PrimeVoiceRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._refresh_snapshot = dict(main.VOICE_REFRESH_STATE)

    async def asyncTearDown(self) -> None:
        main.VOICE_REFRESH_STATE.clear()
        main.VOICE_REFRESH_STATE.update(self._refresh_snapshot)

    async def test_prime_registry_syncs_local_sources(self) -> None:
        enumerator = AsyncMock(return_value=[])
        with patch.object(main, "sync_local_voice_references") as sync_local, patch.object(main, "_enumerate_voices", enumerator):
            await main._prime_voice_registry(force=True)

        sync_local.assert_called_once_with(force=True)
        enumerator.assert_awaited()

    async def test_prime_registry_skips_remote_refresh_when_recent(self) -> None:
        async with main.VOICE_REFRESH_LOCK:
            main.VOICE_REFRESH_STATE["last_refresh"] = time.monotonic()

        with patch.object(main, "sync_local_voice_references") as sync_local, patch.object(main, "_enumerate_voices", AsyncMock()) as enumerator:
            await main._prime_voice_registry(force=False)

        sync_local.assert_called_once_with(force=False)
        enumerator.assert_not_awaited()


class ListVoicesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._map_snapshot = dict(main.VOICE_FILE_MAP)
        self._refresh_snapshot = dict(main.VOICE_REFRESH_STATE)

    async def asyncTearDown(self) -> None:
        main.VOICE_FILE_MAP.clear()
        main.VOICE_FILE_MAP.update(self._map_snapshot)
        main.VOICE_REFRESH_STATE.update(self._refresh_snapshot)

    async def test_list_voices_delegates_to_enumerator(self) -> None:
        expected = [{"id": "v1", "name": "Sample"}]
        enumerator = AsyncMock(return_value=expected)
        with patch.object(main, "_enumerate_voices", enumerator):
            result = await main.list_voices()

        enumerator.assert_awaited()
        self.assertEqual(result, expected)


class SimpleCircuitBreakerTests(unittest.IsolatedAsyncioTestCase):
    async def test_breaker_opens_after_threshold(self) -> None:
        breaker = main.SimpleCircuitBreaker(threshold=2, cooldown_seconds=0.5)
        log = structlog.get_logger("test-breaker")

        await breaker.ensure_available(log)
        await breaker.record_failure(log)
        await breaker.ensure_available(log)
        await breaker.record_failure(log)

        with self.assertRaises(main.HTTPException) as ctx:
            await breaker.ensure_available(log)

        self.assertEqual(ctx.exception.status_code, 503)
        snapshot = await breaker.snapshot()
        self.assertTrue(snapshot["open"])
        self.assertGreater(snapshot["retry_after_s"], 0.0)


class RequestWithRetriesTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._original_client = main._http_client
        self._original_breaker = main.CIRCUIT_BREAKER
        main.CIRCUIT_BREAKER = main.SimpleCircuitBreaker(threshold=3, cooldown_seconds=1)
        async with main.UPSTREAM_STATE_LOCK:
            main.UPSTREAM_STATE["last_success"] = None
            main.UPSTREAM_STATE["last_failure"] = None
            main.UPSTREAM_STATE["consecutive_failures"] = 0

    async def asyncTearDown(self) -> None:
        main._http_client = self._original_client
        main.CIRCUIT_BREAKER = self._original_breaker
        async with main.UPSTREAM_STATE_LOCK:
            main.UPSTREAM_STATE["consecutive_failures"] = 0

    async def test_request_retries_and_records_metrics(self) -> None:
        request = httpx.Request("GET", "http://upstream.test/resource")
        responses = [
            httpx.Response(500, request=request, text="fail"),
            httpx.Response(200, request=request, content=b"ok", headers={"content-type": "text/plain"}),
        ]
        call_index = {"count": 0}

        class DummyClient:
            async def request(self, method: str, url: str, **kwargs):
                idx = call_index["count"]
                call_index["count"] += 1
                return responses[idx]

        dummy_client = DummyClient()

        with patch.object(main, "get_http_client", return_value=dummy_client):
            logger = structlog.get_logger("test-request")
            response = await main._request_with_retries(
                "GET",
                "http://upstream.test/resource",
                logger=logger,
                max_attempts=2,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(call_index["count"], 2)
        async with main.UPSTREAM_STATE_LOCK:
            self.assertEqual(main.UPSTREAM_STATE["consecutive_failures"], 0)
            self.assertIsNotNone(main.UPSTREAM_STATE["last_success"])
            self.assertIsNotNone(main.UPSTREAM_STATE["last_failure"])


class HealthEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        async with main.UPSTREAM_STATE_LOCK:
            now = time.time()
            main.UPSTREAM_STATE["last_success"] = now
            main.UPSTREAM_STATE["last_failure"] = now - 10
            main.UPSTREAM_STATE["consecutive_failures"] = 0

    async def test_health_aggregates_state(self) -> None:
        probe_payload = {
            "reachable": True,
            "http_status": 200,
            "detail": None,
            "payload": {"status": "ok"},
            "checked_at": time.time(),
        }

        with patch.object(main, "_probe_upstream_health", new=AsyncMock(return_value=probe_payload)):
            result = await main.health()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["upstream"], main.UPSTREAM)
        self.assertIn("breaker", result)
        self.assertIn("metrics", result)
        self.assertIn("upstream_probe", result)
        self.assertEqual(result["upstream_probe"], probe_payload)


if __name__ == "__main__":
    unittest.main()
