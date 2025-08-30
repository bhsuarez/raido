import asyncio
import aiofiles
import httpx
import structlog
from pathlib import Path
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime, timedelta
from collections import defaultdict

from app.core.config import settings

logger = structlog.get_logger()

class KokoroClient:
    """Client for Kokoro TTS with circuit breaker protection"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'KOKORO_BASE_URL', 'http://localhost:8090')
        self.voice = getattr(settings, 'KOKORO_VOICE', 'af_bella')
        self.speed = getattr(settings, 'KOKORO_SPEED', 1.0)
        
        # Circuit breaker state
        self._failure_count = 0
        self._last_failure_time = None
        self._circuit_open = False
        self._max_failures = 5
        self._reset_timeout = 300  # 5 minutes
        
        # Rate limiting
        self._request_times = []
        self._max_requests_per_minute = 10
        
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self._circuit_open:
            return False
            
        if self._last_failure_time and \
           datetime.now() - self._last_failure_time > timedelta(seconds=self._reset_timeout):
            logger.info("Circuit breaker reset timeout reached, attempting reset")
            self._circuit_open = False
            self._failure_count = 0
            return False
            
        return True
    
    def _record_failure(self):
        """Record a failure and potentially open circuit"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        if self._failure_count >= self._max_failures:
            self._circuit_open = True
            logger.error("Circuit breaker OPENED", 
                        failures=self._failure_count,
                        timeout_minutes=self._reset_timeout // 60)
    
    def _record_success(self):
        """Record successful operation"""
        self._failure_count = 0
        self._circuit_open = False
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old requests
        self._request_times = [t for t in self._request_times if t > cutoff]
        
        if len(self._request_times) >= self._max_requests_per_minute:
            logger.warning("Rate limit exceeded", 
                          requests_per_minute=len(self._request_times))
            return False
        
        self._request_times.append(now)
        return True

    @retry(
        stop=stop_after_attempt(2),  # Reduced from 3
        wait=wait_exponential(multiplier=2, min=4, max=16),  # Longer waits
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def generate_audio(self, text: str, job_id: str, *, voice: Optional[str] = None, speed: Optional[float] = None) -> Optional[str]:
        """Generate audio using Kokoro TTS with circuit breaker protection"""
        try:
            # Check circuit breaker
            if self._is_circuit_open():
                logger.warning("Circuit breaker is OPEN - skipping TTS request", 
                             failures=self._failure_count)
                return None
            
            # Check rate limiting
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded - skipping TTS request")
                return None
            
            use_voice = voice or self.voice
            use_speed = float(speed) if speed is not None else float(self.speed)
            logger.info("Generating TTS with Kokoro", voice=use_voice, text_length=len(text))
            
            # Create output filename
            filename = f"commentary_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            filepath = Path(settings.TTS_CACHE_DIR) / filename
            
            async with httpx.AsyncClient(timeout=15.0) as client:  # Reduced timeout
                response = await client.post(
                    f"{self.base_url}/v1/audio/speech",
                    json={
                        "input": text,
                        "voice": use_voice,
                        "model": "tts-1",
                        "response_format": "mp3",
                        "speed": use_speed if use_speed else 1.0
                    }
                )
                
                if response.status_code == 200:
                    # Save audio file
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(response.content)
                    
                    logger.info("Kokoro TTS audio generated", 
                               filepath=str(filepath), 
                               size=len(response.content))
                    
                    self._record_success()  # Record successful operation
                    return filename
                else:
                    logger.error("Kokoro TTS error", 
                               status=response.status_code, 
                               response=response.text)
                    self._record_failure()  # Record failure
                    
            return None
            
        except Exception as e:
            logger.error("Kokoro TTS generation failed", error=str(e))
            self._record_failure()  # Record failure
            raise
            
    async def test_connection(self) -> bool:
        """Test if Kokoro TTS is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
