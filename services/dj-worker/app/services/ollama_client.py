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
        # Track recent failures for simple cooldown circuit breaker
        self._failures: deque[float] = deque(maxlen=10)
        self._cooldown_seconds = 300  # 5 minutes
        self._failure_threshold = 3
    
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

            # Stream tokens to avoid long blocking waits
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": use_model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        logger.error("Ollama API error", status=resp.status_code, response=body.decode(errors='ignore'))
                        # Count as failure for cooldown
                        self._failures.append(time.time())
                        return None

                    content_parts: list[str] = []
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        try:
                            import json as _json
                            # Some servers may prefix lines with 'data: '
                            raw = line.strip()
                            if raw.startswith("data: "):
                                raw = raw[6:].strip()
                            if not raw:
                                continue
                            data = _json.loads(raw)
                        except Exception as e:
                            # Log malformed JSON for debugging and continue
                            logger.debug("Skipping malformed JSON line", line=line[:100], error=str(e))
                            continue
                        
                        # Only process valid response objects
                        if not isinstance(data, dict):
                            logger.debug("Skipping non-object response", type=type(data).__name__)
                            continue
                            
                        piece = data.get("response")
                        if isinstance(piece, str) and piece:
                            content_parts.append(piece)
                        if data.get("done") is True:
                            break

            if content_parts:
                content = "".join(content_parts).strip()
                logger.debug("Generated commentary", length=len(content))
                
                # Sanity check: if the content looks like raw JSON, something went wrong
                if content.startswith('{"model":') or content.count('{"model":') > 3:
                    logger.error("Commentary appears to contain raw JSON responses", 
                               content_preview=content[:200])
                    self._failures.append(time.time())
                    return None
                    
                return content
            # No content is a failure; track
            self._failures.append(time.time())
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e))
            try:
                self._failures.append(time.time())
            except Exception:
                pass
            raise
