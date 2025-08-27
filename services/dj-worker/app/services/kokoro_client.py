import asyncio
import aiofiles
import httpx
import structlog
from pathlib import Path
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

from app.core.config import settings

logger = structlog.get_logger()

class KokoroClient:
    """Client for Kokoro TTS"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'KOKORO_BASE_URL', 'http://localhost:8080')
        self.voice = getattr(settings, 'KOKORO_VOICE', 'af_bella')
        self.speed = getattr(settings, 'KOKORO_SPEED', 1.0)
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def generate_audio(self, text: str, job_id: str) -> Optional[str]:
        """Generate audio using Kokoro TTS"""
        try:
            logger.info("Generating TTS with Kokoro", voice=self.voice, text_length=len(text))
            
            # Create output filename
            filename = f"commentary_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            filepath = Path(settings.TTS_CACHE_DIR) / filename
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/audio/speech",
                    json={
                        "input": text,
                        "voice": self.voice,
                        "model": "kokoro-v1_0",
                        "response_format": "mp3"
                    }
                )
                
                if response.status_code == 200:
                    # Save audio file
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(response.content)
                    
                    logger.info("Kokoro TTS audio generated", 
                               filepath=str(filepath), 
                               size=len(response.content))
                    
                    return filename
                else:
                    logger.error("Kokoro TTS error", 
                               status=response.status_code, 
                               response=response.text)
                    
            return None
            
        except Exception as e:
            logger.error("Kokoro TTS generation failed", error=str(e))
            raise
            
    async def test_connection(self) -> bool:
        """Test if Kokoro TTS is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False