import asyncio
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any, Iterable

import httpx
import structlog
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

import shutil

logger = structlog.get_logger()

UPSTREAM = os.getenv("CH_SHIM_UPSTREAM", "http://192.168.1.112:8000").rstrip("/")
READ_TIMEOUT = float(os.getenv("CH_SHIM_TIMEOUT", "60"))
CONNECT_TIMEOUT = float(os.getenv("CH_SHIM_CONNECT_TIMEOUT", "5"))
WRITE_TIMEOUT = float(os.getenv("CH_SHIM_WRITE_TIMEOUT", "10"))
POOL_TIMEOUT = float(os.getenv("CH_SHIM_POOL_TIMEOUT", "5"))
FORCE_MP3 = os.getenv("CH_SHIM_FORCE_MP3", "true").lower() in ("1", "true", "yes", "on")
FFMPEG_PATH = shutil.which("ffmpeg")

HTTP_TIMEOUT = httpx.Timeout(
    connect=CONNECT_TIMEOUT,
    read=READ_TIMEOUT,
    write=WRITE_TIMEOUT,
    pool=POOL_TIMEOUT,
)

MAX_CONNECTIONS = int(os.getenv("CH_SHIM_MAX_CONNECTIONS", "20"))
MAX_KEEPALIVE = int(os.getenv("CH_SHIM_MAX_KEEPALIVE", "10"))
KEEPALIVE_EXPIRY = float(os.getenv("CH_SHIM_KEEPALIVE_EXPIRY", "45"))
HTTP_LIMITS = httpx.Limits(
    max_connections=MAX_CONNECTIONS,
    max_keepalive_connections=MAX_KEEPALIVE,
    keepalive_expiry=KEEPALIVE_EXPIRY,
)

MAX_ATTEMPTS = int(os.getenv("CH_SHIM_MAX_ATTEMPTS", "3"))
BACKOFF_BASE = float(os.getenv("CH_SHIM_BACKOFF_BASE", "0.2"))
BACKOFF_MAX = float(os.getenv("CH_SHIM_BACKOFF_MAX", "5"))
BREAKER_THRESHOLD = int(os.getenv("CH_SHIM_BREAKER_THRESHOLD", "5"))
BREAKER_COOLDOWN = float(os.getenv("CH_SHIM_BREAKER_COOLDOWN", "30"))
HEALTH_CACHE_TTL = float(os.getenv("CH_SHIM_HEALTH_TTL", "10"))

UPLOAD_DIR = Path(os.getenv("CH_SHIM_UPLOAD_DIR", "/root/frontend/uploads")).resolve()
UPLOAD_LOG_PATH = Path(os.getenv("CH_SHIM_UPLOAD_LOG", UPLOAD_DIR / "voice_uploads.json")).resolve()
VOICE_MANIFEST_PATH = Path(os.getenv("CH_SHIM_VOICE_MANIFEST", "/shared/voice_references/voice_manifest.json")).resolve()
VOICE_MAP_ENV = os.getenv("CH_SHIM_VOICE_MAP")
LOCAL_REFRESH_INTERVAL = float(os.getenv("CH_SHIM_LOCAL_REFRESH_INTERVAL", "3"))

# Stores case-insensitive lookups from voice identifiers to prompt file paths
VOICE_FILE_MAP: dict[str, str] = {}
VOICE_REFRESH_LOCK = asyncio.Lock()
VOICE_REFRESH_STATE = {"last_refresh": 0.0, "last_local_sync": 0.0}


def _normalize_voice_key(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.lower()


def _normalize_audio_path(path: str | None) -> str | None:
    if not path:
        return None
    raw = str(path).strip()
    if not raw:
        return None
    if raw.startswith("/"):
        return raw
    # Treat relative paths as residing in the configured upload directory
    return str((UPLOAD_DIR / raw).resolve())


def register_voice_reference(
    voice_id: str | None = None,
    voice_name: str | None = None,
    audio_prompt_path: str | None = None,
) -> None:
    path = _normalize_audio_path(audio_prompt_path)
    if not path:
        return

    for candidate in filter(None, {_normalize_voice_key(voice_id), _normalize_voice_key(voice_name)}):
        VOICE_FILE_MAP[candidate] = path


def resolve_audio_prompt(voice_key: str | None) -> str | None:
    normalized = _normalize_voice_key(voice_key)
    if not normalized:
        return None
    return VOICE_FILE_MAP.get(normalized)


def _register_from_iterable(items: Iterable[Any]) -> None:
    for item in items:
        if isinstance(item, dict):
            voice_id = item.get("id") or item.get("voice_id") or item.get("voice")
            voice_name = item.get("name") or item.get("label") or item.get("display_name") or item.get("title")
            audio_prompt_path = (
                item.get("audio_prompt_path")
                or item.get("file_path")
                or item.get("path")
                or item.get("sample_path")
            )
            register_voice_reference(voice_id, voice_name, audio_prompt_path)
        elif isinstance(item, str):
            # String-only entries indicate a voice identifier without prompt metadata.
            register_voice_reference(item, item, None)


def _ingest_voice_manifest(payload: Any) -> None:
    if payload is None:
        return
    if isinstance(payload, dict):
        voices = payload.get("voices")
        if isinstance(voices, list):
            _register_from_iterable(voices)
            return
        # Some servers return a mapping of id -> metadata
        _register_from_iterable(payload.values())
    elif isinstance(payload, list):
        _register_from_iterable(payload)


def _load_voice_manifest_from_file(path: Path) -> None:
    try:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        _ingest_voice_manifest(payload)
    except Exception as exc:
        logger.warning("Failed to load voice manifest", path=str(path), error=str(exc))


def _load_voice_references_from_upload_log(path: Path) -> None:
    try:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        voices = []
        if isinstance(payload, list):
            voices = payload
        elif isinstance(payload, dict):
            voices = payload.get("voices") or payload.get("entries") or []
        _register_from_iterable(voices if isinstance(voices, list) else [])
    except Exception as exc:
        logger.warning("Failed to parse upload log", path=str(path), error=str(exc))


def refresh_voice_map_from_disk() -> None:
    try:
        if not UPLOAD_DIR.exists():
            return
        patterns = ("*.wav", "*.mp3", "*.ogg", "*.flac")
        for pattern in patterns:
            for filepath in UPLOAD_DIR.glob(pattern):
                stem = filepath.stem
                voice_id = None
                voice_name = None
                if "_" in stem:
                    parts = stem.split("_", 1)
                    voice_id, voice_name = parts[0], parts[1]
                else:
                    voice_name = stem
                register_voice_reference(voice_id, voice_name, str(filepath.resolve()))
    except Exception as exc:
        logger.warning("Failed to scan upload directory for voice prompts", directory=str(UPLOAD_DIR), error=str(exc))


def _load_voice_map_from_env() -> None:
    if not VOICE_MAP_ENV:
        return
    try:
        mapping = json.loads(VOICE_MAP_ENV)
        if isinstance(mapping, dict):
            for key, value in mapping.items():
                register_voice_reference(str(key), None, str(value))
            return
    except json.JSONDecodeError:
        pass

    # Support simple semi-colon separated "voice=path" pairs if JSON parsing fails.
    for chunk in VOICE_MAP_ENV.split(";"):
        if not chunk.strip():
            continue
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        register_voice_reference(key, None, value)


def sync_local_voice_references(*, force: bool = False) -> None:
    """Populate the in-memory voice map from local metadata sources."""
    now = time.monotonic()
    last_sync = VOICE_REFRESH_STATE.get("last_local_sync", 0.0)
    if not force and (now - last_sync) < LOCAL_REFRESH_INTERVAL:
        return

    refresh_voice_map_from_disk()
    _load_voice_references_from_upload_log(UPLOAD_LOG_PATH)
    _load_voice_manifest_from_file(VOICE_MANIFEST_PATH)
    _load_voice_map_from_env()
    VOICE_REFRESH_STATE["last_local_sync"] = now


def bootstrap_voice_registry() -> None:
    sync_local_voice_references(force=True)


bootstrap_voice_registry()

_http_client: httpx.AsyncClient | None = None


class SimpleCircuitBreaker:
    def __init__(self, threshold: int, cooldown_seconds: float) -> None:
        self._threshold = max(1, threshold)
        self._cooldown = max(0.0, cooldown_seconds)
        self._failures = 0
        self._open_until = 0.0
        self._lock = asyncio.Lock()

    async def ensure_available(self, log: structlog.typing.FilteringBoundLogger | None = None) -> None:
        async with self._lock:
            now = time.monotonic()
            if self._open_until > now:
                retry_after = max(0.0, self._open_until - now)
                if log is not None:
                    log.warning("Circuit breaker open", retry_after=round(retry_after, 2))
                raise HTTPException(status_code=503, detail="Upstream temporarily unavailable")

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._open_until = 0.0

    async def record_failure(self, log: structlog.typing.FilteringBoundLogger | None = None) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._open_until = time.monotonic() + self._cooldown
                self._failures = 0
                if log is not None:
                    log.warning(
                        "Circuit breaker tripped",
                        cooldown_s=round(self._cooldown, 2),
                    )

    async def snapshot(self) -> dict[str, float | int | bool]:
        async with self._lock:
            now = time.monotonic()
            open_state = self._open_until > now
            retry_after = max(0.0, self._open_until - now) if open_state else 0.0
            return {
                "open": open_state,
                "retry_after_s": round(retry_after, 3),
                "threshold": self._threshold,
                "cooldown_s": self._cooldown,
                "pending_failures": self._failures,
            }


CIRCUIT_BREAKER = SimpleCircuitBreaker(BREAKER_THRESHOLD, BREAKER_COOLDOWN)
UPSTREAM_STATE = {
    "last_success": None,
    "last_failure": None,
    "consecutive_failures": 0,
}
UPSTREAM_STATE_LOCK = asyncio.Lock()

HEALTH_CACHE: dict[str, object] = {"timestamp": 0.0, "payload": None}
HEALTH_CACHE_LOCK = asyncio.Lock()

FALLBACK_VOICES = [
    {
        "id": "d92260ce-6412-48d9-b348-d1d0706f4fbf",
        "name": "brian",
        "audio_prompt_path": "/root/frontend/uploads/d92260ce-6412-48d9-b348-d1d0706f4fbf_brian.wav",
    },
    {
        "id": "cb231744-e7c6-4f56-9aaa-593720b38928",
        "name": "natalie",
        "audio_prompt_path": "/root/frontend/uploads/cb231744-e7c6-4f56-9aaa-593720b38928_natalie.wav",
    },
]

# Seed the registry with known fallback voices on startup
_register_from_iterable(FALLBACK_VOICES)


async def transcode_wav_to_mp3(
    data: bytes,
    log: structlog.typing.FilteringBoundLogger | structlog.BoundLogger | None = None,
) -> bytes | None:
    """Transcode WAV bytes to MP3 asynchronously if ffmpeg is available."""
    if not FFMPEG_PATH:
        return None
    logger_ref = log or logger
    try:
        process = await asyncio.create_subprocess_exec(
            FFMPEG_PATH,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            "-f",
            "mp3",
            "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(input=data)
        if process.returncode != 0:
            logger_ref.warning(
                "ffmpeg transcode failed; returning original",
                error=stderr.decode("utf-8", "ignore")[:200],
            )
            return None
        return stdout
    except Exception as exc:
        logger_ref.warning("ffmpeg transcode failed; returning original", error=str(exc))
        return None


async def _mark_upstream_success() -> None:
    async with UPSTREAM_STATE_LOCK:
        UPSTREAM_STATE["last_success"] = time.time()
        UPSTREAM_STATE["consecutive_failures"] = 0


async def _mark_upstream_failure() -> None:
    async with UPSTREAM_STATE_LOCK:
        UPSTREAM_STATE["last_failure"] = time.time()
        UPSTREAM_STATE["consecutive_failures"] = UPSTREAM_STATE.get("consecutive_failures", 0) + 1


async def _probe_upstream_health() -> dict[str, object]:
    now = time.monotonic()
    async with HEALTH_CACHE_LOCK:
        cached_payload = HEALTH_CACHE.get("payload")
        cached_ts = HEALTH_CACHE.get("timestamp", 0.0)
        if cached_payload is not None and (now - cached_ts) < HEALTH_CACHE_TTL:
            return cached_payload  # type: ignore[return-value]

        probe_logger = logger.bind(route="/health", action="probe")
        reachable = False
        http_status: int | None = None
        detail: str | None = None
        payload: object | None = None

        probe_timeout = httpx.Timeout(
            connect=min(CONNECT_TIMEOUT, 2.0),
            read=min(READ_TIMEOUT, 5.0),
            write=min(WRITE_TIMEOUT, 5.0),
            pool=POOL_TIMEOUT,
        )

        try:
            response = await _request_with_retries(
                "GET",
                f"{UPSTREAM}/health",
                logger=probe_logger,
                max_attempts=1,
                timeout=probe_timeout,
            )
            http_status = response.status_code
            if response.status_code == 200:
                reachable = True
                try:
                    payload = response.json()
                except ValueError:
                    payload = response.text[:200]
            else:
                payload = response.text[:200]
        except HTTPException as exc:
            http_status = exc.status_code
            detail = str(exc.detail)
        except Exception as exc:
            detail = str(exc)

        result = {
            "reachable": reachable,
            "http_status": http_status,
            "detail": detail,
            "payload": payload,
            "checked_at": time.time(),
        }
        HEALTH_CACHE["timestamp"] = now
        HEALTH_CACHE["payload"] = result
        return result


async def _request_with_retries(
    method: str,
    url: str,
    *,
    logger: structlog.typing.FilteringBoundLogger | structlog.BoundLogger,
    max_attempts: int | None = None,
    **kwargs,
) -> httpx.Response:
    attempts = max(1, max_attempts or MAX_ATTEMPTS)
    client = get_http_client()
    backoff = BACKOFF_BASE
    for attempt in range(1, attempts + 1):
        await CIRCUIT_BREAKER.ensure_available(logger)
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            await CIRCUIT_BREAKER.record_failure(logger)
            await _mark_upstream_failure()
            if attempt == attempts:
                raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc
            wait_time = min(backoff + random.uniform(0, BACKOFF_BASE), BACKOFF_MAX)
            logger.warning(
                "Upstream request error",
                method=method,
                url=url,
                attempt=attempt,
                max_attempts=attempts,
                backoff_s=round(wait_time, 2),
                error=str(exc),
            )
            await asyncio.sleep(wait_time)
            backoff = min(backoff * 2, BACKOFF_MAX)
            continue

        if response.status_code >= 500:
            await CIRCUIT_BREAKER.record_failure(logger)
            await _mark_upstream_failure()
            if attempt == attempts:
                return response
            wait_time = min(backoff + random.uniform(0, BACKOFF_BASE), BACKOFF_MAX)
            logger.warning(
                "Upstream returned error status",
                method=method,
                url=url,
                status=response.status_code,
                attempt=attempt,
                max_attempts=attempts,
                backoff_s=round(wait_time, 2),
            )
            await asyncio.sleep(wait_time)
            backoff = min(backoff * 2, BACKOFF_MAX)
            continue

        await CIRCUIT_BREAKER.record_success()
        await _mark_upstream_success()
        return response

    raise HTTPException(status_code=502, detail="Upstream request failed after retries")

app = FastAPI(title="Chatterbox Compatibility Shim")


@app.on_event("startup")
async def _startup_http_client() -> None:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS)


@app.on_event("shutdown")
async def _shutdown_http_client() -> None:
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS)
    return _http_client

class SpeakRequest(BaseModel):
    text: str
    voice_id: str

@app.get("/health")
async def health():
    probe = await _probe_upstream_health()
    breaker_state = await CIRCUIT_BREAKER.snapshot()
    async with UPSTREAM_STATE_LOCK:
        metrics_snapshot = {
            "last_success": UPSTREAM_STATE.get("last_success"),
            "last_failure": UPSTREAM_STATE.get("last_failure"),
            "consecutive_failures": UPSTREAM_STATE.get("consecutive_failures", 0),
        }

    status = "ok" if probe.get("reachable") else "degraded"
    if breaker_state.get("open"):
        status = "degraded"

        return {
            "status": status,
            "upstream": UPSTREAM,
            "breaker": breaker_state,
            "metrics": metrics_snapshot,
            "upstream_probe": probe,
        }


async def _enumerate_voices(
    log: structlog.typing.FilteringBoundLogger | structlog.BoundLogger | None = None,
) -> Any:
    voice_logger = (log or logger).bind(action="enumerate_voices")
    await CIRCUIT_BREAKER.ensure_available(voice_logger)
    endpoints = ["/voices", "/api/voices", "/v1/voices", "/list_voices", "/v1/audio/voices"]

    for endpoint in endpoints:
        endpoint_logger = voice_logger.bind(endpoint=endpoint)
        try:
            response = await _request_with_retries(
                "GET",
                f"{UPSTREAM}{endpoint}",
                logger=endpoint_logger,
                max_attempts=2,
            )
        except HTTPException:
            raise
        except Exception as exc:
            endpoint_logger.debug("Voice endpoint request error", error=str(exc))
            continue

        if response.status_code == 200:
            try:
                data = response.json()
            except Exception as exc:
                endpoint_logger.warning(
                    "Voice endpoint returned invalid JSON",
                    error=str(exc),
                    preview=response.text[:200],
                )
                continue

            _ingest_voice_manifest(data)
            VOICE_REFRESH_STATE["last_refresh"] = time.monotonic()
            return data

        endpoint_logger.debug("Voice endpoint returned non-200", status=response.status_code)

    # Fallback to known static voices when upstream offers no metadata.
    voice_logger.warning("No voice endpoints available, using fallback voices")
    _ingest_voice_manifest(FALLBACK_VOICES)
    VOICE_REFRESH_STATE["last_refresh"] = time.monotonic()
    return FALLBACK_VOICES


async def _prime_voice_registry(
    log: structlog.typing.FilteringBoundLogger | structlog.BoundLogger | None = None,
    *,
    force: bool = False,
) -> None:
    async with VOICE_REFRESH_LOCK:
        sync_local_voice_references(force=force)
        now = time.monotonic()
        if not force and (now - VOICE_REFRESH_STATE.get("last_refresh", 0.0)) < 5.0:
            return
        try:
            await _enumerate_voices(log)
        except Exception as exc:
            VOICE_REFRESH_STATE["last_refresh"] = now
            (log or logger).debug("Voice registry refresh failed", error=str(exc))


async def _attach_audio_prompt(
    metadata: dict[str, Any],
    voice_hint: str | None,
    log: structlog.typing.FilteringBoundLogger | structlog.BoundLogger | None = None,
) -> None:
    if voice_hint is None:
        return

    sync_local_voice_references()

    # Attempt direct lookup first
    audio_path = resolve_audio_prompt(voice_hint)

    if audio_path is None:
        # Ensure we have the latest voice catalog before giving up
        await _prime_voice_registry(log)
        audio_path = resolve_audio_prompt(voice_hint)

    if audio_path is None and "_" in voice_hint:
        # Many uploaded prompts follow `<uuid>_<alias>` naming; try alias component
        alias = voice_hint.split("_", 1)[-1]
        audio_path = resolve_audio_prompt(alias)

    if audio_path:
        metadata["audio_prompt_path"] = audio_path


async def _call_upstream_tts(params: dict, bound_logger: structlog.typing.FilteringBoundLogger | None = None) -> Response:
    def _sniff_ext(data: bytes, content_type: str | None) -> tuple[str, str]:
        ct = (content_type or "").lower()
        head = data[:16] if data else b""
        try:
            if head.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
                return ("wav", "audio/wav")
            if head.startswith(b"ID3"):
                return ("mp3", "audio/mpeg")
            if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
                return ("mp3", "audio/mpeg")
            if head.startswith(b"OggS"):
                return ("ogg", "audio/ogg")
            if head.startswith(b"fLaC"):
                return ("flac", "audio/flac")
        except Exception:
            pass
        if ct == "audio/mpeg":
            return ("mp3", "audio/mpeg")
        if ct in ("audio/wav", "audio/wave"):
            return ("wav", "audio/wav")
        return ("bin", ct or "application/octet-stream")

    log = (bound_logger or logger).bind(route="/tts", voice=params.get("voice"))
    started = time.monotonic()
    log.info("Calling legacy TTS endpoint", upstream=UPSTREAM, params_sent=list(params.keys()))
    r = await _request_with_retries("GET", f"{UPSTREAM}/tts", logger=log, params=params)
    elapsed = time.monotonic() - started
    log.info(
        "Legacy TTS response received",
        status=r.status_code,
        duration_s=round(elapsed, 3),
        bytes=len(r.content or b""),
        content_type=r.headers.get("content-type"),
    )
    if r.status_code == 200:
        content_type = (r.headers.get("content-type", "") or "").lower()
        data = r.content
        # If forcing MP3 and upstream returned WAV, transcode
        ext, sniffed = _sniff_ext(data, content_type)
        if FORCE_MP3 and ext != "mp3" and ext == "wav":
            transcoded = await transcode_wav_to_mp3(data, log)
            if transcoded:
                data = transcoded
                content_type = "audio/mpeg"
                logger.info("Shim transcoded WAV->MP3 via ffmpeg (GET)", bytes=len(data))
        # Validate Content-Type to ensure it's audio (do NOT accept arbitrary content)
        if "audio" in content_type or content_type == "application/octet-stream":
            if content_type == "application/octet-stream":
                content_type = "audio/mpeg" if FORCE_MP3 else (sniffed or "audio/wav")
            return Response(content=data, media_type=content_type)
        backend_preview = r.text[:200] if r.text else "Unknown backend error"
        logger.error("Chatterbox returned non-audio content", content_type=content_type, preview=backend_preview)
        raise HTTPException(status_code=502, detail=f"Backend returned non-audio content. Backend preview: {backend_preview}")
    log.warning("Legacy TTS upstream failure", status=r.status_code, preview=r.text[:200])
    raise HTTPException(status_code=r.status_code, detail=r.text[:200])

@app.post("/v1/audio/speech")
async def v1_audio_speech(
    input: str = Form(...),
    voice: str = Form("default"),
    response_format: str = Form("mp3"),
    model: str = Form("tts-1"),
    exaggeration: float = Form(1.0),
    cfg_weight: float = Form(0.5),
    audio: UploadFile | None = File(None),
):
    request_id = uuid.uuid4().hex[:8]
    req_logger = logger.bind(route="/v1/audio/speech", request_id=request_id, voice=voice)
    try:
        # Prefer WAV upstream for stability; transcode to MP3 locally if configured
        order = []
        req_fmt = (response_format or "").lower()
        if req_fmt == "mp3":
            order = ["mp3", "wav"]
        else:
            # Default to WAV first if not explicitly requesting MP3
            order = ["wav", "mp3"]

        base_payload = {
            "input": input,
            "voice": voice,
            "model": model,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
        }
        await _attach_audio_prompt(base_payload, voice, req_logger)
        for fmt in order:
            try:
                started = time.monotonic()
                payload = dict(base_payload)
                payload["response_format"] = fmt
                req_logger.info("Calling upstream Chatterbox", fmt=fmt, upstream=UPSTREAM)
                r = await _request_with_retries(
                    "POST",
                    f"{UPSTREAM}/v1/audio/speech",
                    logger=req_logger,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                elapsed = time.monotonic() - started
                req_logger.info(
                    "Upstream response received",
                    fmt=fmt,
                    status=r.status_code,
                    duration_s=round(elapsed, 3),
                    bytes=len(r.content or b""),
                    content_type=r.headers.get("content-type"),
                )
            except HTTPException:
                raise
            except Exception as e:
                req_logger.warning("Upstream POST /v1/audio/speech error", fmt=fmt, error=str(e))
                continue

            if r.status_code == 200 and r.content:
                content_type = (r.headers.get("content-type", "") or "").lower()
                data = r.content
                # Force MP3 if configured and upstream returned WAV
                if fmt == "wav" and FORCE_MP3:
                    transcoded = await transcode_wav_to_mp3(data, req_logger)
                    if transcoded:
                        data = transcoded
                        content_type = "audio/mpeg"
                        req_logger.info("Shim transcoded WAV->MP3 via ffmpeg (v1)", bytes=len(data))
                if content_type == "application/octet-stream":
                    content_type = "audio/mpeg" if (FORCE_MP3 or fmt == "mp3") else "audio/wav"
                # Only accept audio content types
                if ("audio" in content_type) or (content_type == "application/octet-stream"):
                    req_logger.info("Returning audio to caller", fmt=fmt, media_type=content_type, bytes=len(data))
                    return Response(content=data, media_type=content_type)
                else:
                    backend_preview = r.text[:200] if r.text else "Unknown backend error"
                    req_logger.error("Chatterbox returned non-audio in v1/audio/speech", content_type=content_type, preview=backend_preview)
                    continue

            # If MP3 not supported, try WAV next
            if fmt == "mp3" and r.status_code in (415, 501):
                req_logger.warning("Upstream does not support MP3; retrying WAV (v1)", status=r.status_code)
                continue
            req_logger.warning("Upstream POST /v1/audio/speech failed", status=r.status_code, fmt=fmt, detail=r.text[:120])

        # Fallback to legacy GET /tts
        params = {
            "text": input,
            "voice": voice,
            "exaggeration": str(exaggeration),
            "cfg_weight": str(cfg_weight),
            "response_format": response_format or "mp3",
        }
        await _attach_audio_prompt(params, voice, req_logger)
        return await _call_upstream_tts(params, bound_logger=req_logger)
    except HTTPException:
        raise
    except Exception as e:
        req_logger.error("Shim /v1/audio/speech failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Shim error: {str(e)}")

@app.get("/tts")
async def tts_get(
    text: str,
    voice: str = "default",
    exaggeration: float = 1.0,
    cfg_weight: float = 0.5,
): 
    params = {
        "text": text,
        "voice": voice,
        "exaggeration": str(exaggeration),
        "cfg_weight": str(cfg_weight),
    }
    request_id = uuid.uuid4().hex[:8]
    bound_logger = logger.bind(route="/tts:get", request_id=request_id, voice=voice)
    await _attach_audio_prompt(params, voice, bound_logger)
    return await _call_upstream_tts(params, bound_logger=bound_logger)

@app.post("/tts")
async def tts_post(request: Request):
    # Accept form and proxy as GET to upstream
    form = await request.form()
    text = form.get("text")
    if not text:
        raise HTTPException(status_code=400, detail="Missing text")
    voice = form.get("voice", "default")
    exaggeration = form.get("exaggeration", "1.0")
    cfg_weight = form.get("cfg_weight", "0.5")
    params = {
        "text": text,
        "voice": voice,
        "exaggeration": exaggeration,
        "cfg_weight": cfg_weight,
    }
    request_id = uuid.uuid4().hex[:8]
    bound_logger = logger.bind(route="/tts:post", request_id=request_id, voice=voice)
    await _attach_audio_prompt(params, voice, bound_logger)
    return await _call_upstream_tts(params, bound_logger=bound_logger)

@app.get("/api/voices")
async def list_voices():
    """List available voices from Chatterbox backend"""
    try:
        voice_logger = logger.bind(route="/api/voices")
        data = await _enumerate_voices(voice_logger)
        # Ensure the result is JSON-serializable (lists/dicts already handled upstream)
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list voices", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve voices: {str(e)}")

@app.post("/api/speak")
async def speak(request: SpeakRequest):
    """Generate TTS using voice_id"""
    request_id = uuid.uuid4().hex[:8]
    req_logger = logger.bind(route="/api/speak", request_id=request_id, voice=request.voice_id)
    try:
        # Build parameters for the legacy /tts endpoint first since it understands audio_prompt_path
        tts_params: dict[str, Any] = {
            "text": request.text,
            "voice": request.voice_id or "default",
        }
        if FORCE_MP3:
            tts_params["response_format"] = "mp3"
        await _attach_audio_prompt(tts_params, request.voice_id, req_logger)
        req_logger.info(
            "Proxying speak request",
            upstream=UPSTREAM,
            text_len=len(request.text or ""),
            using_tts_endpoint=True,
            has_prompt=bool(tts_params.get("audio_prompt_path")),
        )

        try:
            return await _call_upstream_tts(tts_params, bound_logger=req_logger)
        except HTTPException as http_exc:
            # Bubble client errors (bad request, missing prompt) to the caller
            if http_exc.status_code and http_exc.status_code < 500:
                raise
            req_logger.warning(
                "GET /tts failed; falling back to /v1/audio/speech",
                status=http_exc.status_code,
                detail=str(http_exc.detail),
            )
        except Exception as exc:
            req_logger.warning(
                "GET /tts threw unexpected error; falling back to /v1/audio/speech",
                error=str(exc),
            )

        # Use OpenAI-compatible endpoint as fallback when /tts is unavailable
        payload = {
            "input": request.text,
            "voice": request.voice_id or "default",
            # Prefer compressed output from upstream to reduce size/latency
            "response_format": "mp3",
            "model": "tts-1",
        }
        await _attach_audio_prompt(payload, request.voice_id, req_logger)

        # Prefer WAV first for stability; then fallback to MP3 if needed
        for fmt in ("wav", "mp3"):
            try:
                started = time.monotonic()
                payload["response_format"] = fmt
                req_logger.info("Calling upstream Chatterbox", fmt=fmt, upstream=UPSTREAM)
                r = await _request_with_retries(
                    "POST",
                    f"{UPSTREAM}/v1/audio/speech",
                    logger=req_logger,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                elapsed = time.monotonic() - started
                req_logger.info(
                    "Upstream response received",
                    fmt=fmt,
                    status=r.status_code,
                    duration_s=round(elapsed, 3),
                    bytes=len(r.content or b""),
                    content_type=r.headers.get("content-type"),
                )
            except HTTPException:
                raise
            except Exception as e:
                req_logger.warning("Upstream POST /v1/audio/speech error", fmt=fmt, error=str(e))
                continue
            if r.status_code == 200:
                content_type = (r.headers.get("content-type", "") or "").lower()
                # Only accept if content-type indicates audio; otherwise try next format
                if ("audio" in content_type or content_type == "application/octet-stream"):
                    data = r.content
                    # If upstream returned WAV and we prefer MP3, transcode locally if ffmpeg is available
                    if fmt == "wav" and FORCE_MP3:
                        transcoded = await transcode_wav_to_mp3(data, req_logger)
                        if transcoded:
                            data = transcoded
                            content_type = "audio/mpeg"
                            req_logger.info("Shim transcoded WAV->MP3 via ffmpeg", bytes=len(data))
                    # Normalize mime when upstream returns octet-stream
                    if content_type == "application/octet-stream":
                        content_type = "audio/mpeg" if fmt == "mp3" else "audio/wav"
                    req_logger.info("Returning audio to caller", fmt=fmt, media_type=content_type, bytes=len(data))
                    return Response(content=data, media_type=content_type or ("audio/mpeg" if fmt == "mp3" else "audio/wav"))
                backend_preview = r.text[:200] if r.text else "Unknown backend error"
                req_logger.error(
                    "Chatterbox returned non-audio in /v1/audio/speech",
                    content_type=content_type,
                    preview=backend_preview,
                )
                # Try next format if available
                continue
            # If MP3 is not supported, try WAV next; otherwise bubble error
            if fmt == "mp3" and r.status_code in (415, 501):
                req_logger.warning("Upstream does not support MP3; retrying WAV", status=r.status_code)
                continue
            # Final error for this format, try next (or fallback after loop)
            req_logger.warning("Upstream POST /v1/audio/speech failed", status=r.status_code, fmt=fmt, detail=r.text[:120])

        # If we reach here, attempt legacy GET /tts as final chance
        try:
            params = {
                "text": request.text,
                "voice": (request.voice_id or "default"),
            }
            await _attach_audio_prompt(params, request.voice_id, req_logger)
            return await _call_upstream_tts(params, bound_logger=req_logger)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"No valid audio returned from upstream: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        req_logger.error("Speak endpoint failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Speak error: {str(e)}")

@app.post("/api/upload-voice")
async def upload_voice(
    wav_file: UploadFile = File(...),
    voice_name: str = Form(None)
):
    """Upload a voice sample to Chatterbox backend"""
    try:
        # For now, return a placeholder since actual upload would require
        # backend support for voice uploads
        logger.info("Voice upload requested", filename=wav_file.filename, voice_name=voice_name)

        # Generate a mock ID for the uploaded voice
        import uuid
        voice_id = str(uuid.uuid4())

        return {
            "id": voice_id,
            "name": voice_name or wav_file.filename,
            "status": "uploaded",
            "message": "Voice upload functionality would require backend support"
        }

    except Exception as e:
        logger.error("Voice upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")
