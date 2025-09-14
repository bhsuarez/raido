import asyncio
from typing import Optional, AsyncGenerator
import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
import time
from collections import deque

logger = structlog.get_logger()

class OllamaClient:
    """Client for Ollama API interactions"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.last_mode: str | None = None  # 'stream' | 'nonstream' | None
        # Track recent failures for simple cooldown circuit breaker
        self._failures: deque[float] = deque(maxlen=10)
        # Cooldown after repeated failures to avoid hammering the server
        # Use a short cooldown so brief blips don't force long template fallbacks
        self._cooldown_seconds = 30  # seconds
        self._failure_threshold = 3

    def _ollama_options(self, *, temperature: float, num_predict: int) -> dict:
        """Build tuned generation options for Ollama.

        Defaults favor concise, stable outputs suitable for TTS.
        """
        # Clamp reasonable bounds
        try:
            t = max(0.0, min(float(temperature), 1.5))
        except Exception:
            t = 0.8
        try:
            npredict = max(16, min(int(num_predict), 300))
        except Exception:
            npredict = 120
        return {
            "temperature": t,
            "num_predict": npredict,
            # Light guidance for stable speech-y text
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.08,
        }
    
    async def warmup(self) -> None:
        """Warm up the Ollama model to reduce first-request latency."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": "You are a DJ. Respond with OK.",
                        "stream": False,
                        "options": {"num_predict": 5, "temperature": 0.0},
                    },
                )
        except Exception:
            # Best-effort warmup; ignore failures
            pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_commentary(
        self, 
        prompt: str, 
        max_tokens: int = 200,
        temperature: float = 0.8,
        model: Optional[str] = None
    ) -> Optional[str]:
        """Generate DJ commentary text using Ollama"""
        try:
            # Use provided model or fall back to default
            use_model = model or self.model
            
            logger.debug("Generating commentary with Ollama", 
                        model=use_model,
                        max_tokens=max_tokens)

            # Simple circuit breaker: if too many failures recently, skip to fallback
            now = time.time()
            while self._failures and (now - self._failures[0]) > self._cooldown_seconds:
                self._failures.popleft()
            if len(self._failures) >= self._failure_threshold:
                logger.warning(
                    "Skipping Ollama call due to recent failures",
                    recent_failures=len(self._failures),
                    cooldown_seconds=self._cooldown_seconds,
                )
                return None

            # Prefer streaming to keep latency low; on any issue, fall back to non-streaming
            content_parts: list[str] = []
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=90.0, write=60.0)) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/api/generate",
                        json={
                            "model": use_model,
                            "prompt": prompt,
                            "stream": True,
                            "options": self._ollama_options(temperature=temperature, num_predict=max_tokens),
                        },
                    ) as resp:
                        if resp.status_code != 200:
                            body = await resp.aread()
                            logger.warning("Ollama streaming error; will retry non-streaming",
                                           status=resp.status_code,
                                           response=body.decode(errors='ignore')[:200])
                        else:
                            async for line in resp.aiter_lines():
                                if not line:
                                    continue
                                try:
                                    import json as _json
                                    raw = line.strip()
                                    if raw.startswith("data: "):
                                        raw = raw[6:].strip()
                                    if not raw:
                                        continue
                                    data = _json.loads(raw)
                                except Exception as e:
                                    logger.debug("Skipping malformed JSON line", line=line[:100], error=str(e))
                                    continue
                                if not isinstance(data, dict):
                                    logger.debug("Skipping non-object response", type=type(data).__name__)
                                    continue
                                piece = data.get("response")
                                if isinstance(piece, str) and piece:
                                    content_parts.append(piece)
                                if data.get("done") is True:
                                    break
                            # We got streamed content
                            if content_parts:
                                self.last_mode = 'stream'
            except Exception as se:
                logger.warning("Ollama streaming request failed; will try non-streaming", error=str(se))

            # If streaming yielded no content, try a non-streaming call once
            if not content_parts:
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=90.0, write=60.0)) as client:
                        resp = await client.post(
                            f"{self.base_url}/api/generate",
                            json={
                                "model": use_model,
                                "prompt": prompt,
                                "stream": False,
                                "options": self._ollama_options(temperature=temperature, num_predict=max_tokens),
                            },
                        )
                        if resp.status_code == 200:
                            import json as _json
                            try:
                                data = resp.json()
                            except Exception:
                                # Some servers may return NDJSON-like outputs even when stream=false; try best-effort
                                text = (await resp.aread()).decode(errors='ignore')
                                try:
                                    data = _json.loads(text)
                                except Exception:
                                    data = {"response": text}
                            # The non-streaming response typically has a single 'response' string
                            nonstream_text = data.get("response") if isinstance(data, dict) else None
                            if isinstance(nonstream_text, str) and nonstream_text.strip():
                                content_parts = [nonstream_text]
                                self.last_mode = 'nonstream'
                            else:
                                logger.error("Ollama non-streaming response missing 'response' field",
                                             preview=str(data)[:200])
                        else:
                            logger.error("Ollama non-streaming error",
                                         status=resp.status_code,
                                         body=(await resp.aread()).decode(errors='ignore')[:200])
                except Exception as nse:
                    logger.error("Ollama non-streaming request failed", error=str(nse))

            if content_parts:
                content = "".join(content_parts).strip()
                logger.debug("Generated commentary", length=len(content))
                # Reset failures on success
                try:
                    self._failures.clear()
                except Exception:
                    pass
                # Sanity check: if the content looks like raw JSON, something went wrong
                if content.startswith('{"model":') or content.count('{"model":') > 3:
                    logger.error("Commentary appears to contain raw JSON responses",
                                 content_preview=content[:200])
                    self._failures.append(time.time())
                    return None
                return content
            # No content is a failure; track
            self._failures.append(time.time())
            logger.error("Ollama produced no content", base_url=self.base_url, model=use_model)
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e), base_url=self.base_url, model=use_model)
            try:
                self._failures.append(time.time())
            except Exception:
                pass
            raise
