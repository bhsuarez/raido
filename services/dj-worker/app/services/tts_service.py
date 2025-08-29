import os
import asyncio
import aiofiles
from typing import Optional
import structlog
from datetime import datetime

from app.core.config import settings
from app.services.kokoro_client import KokoroClient

logger = structlog.get_logger()

class TTSService:
    """Text-to-Speech service with multiple provider support"""
    
    def __init__(self):
        self.kokoro_client = KokoroClient()
        
        # Try to ensure TTS cache directory exists
        try:
            os.makedirs(settings.TTS_CACHE_DIR, exist_ok=True)
            logger.info("TTS cache directory ready", dir=settings.TTS_CACHE_DIR)
        except PermissionError as e:
            logger.error("Cannot create TTS cache directory", dir=settings.TTS_CACHE_DIR, error=str(e))
            raise
    
    async def generate_audio(self, text: str, job_id: str) -> Optional[str]:
        """Generate audio from text using the configured TTS provider"""
        try:
            provider = settings.DJ_VOICE_PROVIDER
            
            if provider == "kokoro":
                return await self._generate_with_kokoro(text, job_id)
            elif provider == "liquidsoap":
                return await self._generate_with_liquidsoap(text, job_id)
            elif provider == "xtts":
                return await self._generate_with_xtts(text, job_id)
            else:
                logger.error("No valid TTS provider configured", provider=provider)
                return None
        
        except Exception as e:
            logger.error("TTS generation failed", error=str(e), provider=provider)
            return None
    
    
    async def _generate_with_kokoro(self, text: str, job_id: str) -> Optional[str]:
        """Generate audio using Kokoro TTS"""
        try:
            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')
            
            filename = await self.kokoro_client.generate_audio(clean_text, job_id)
            
            if filename:
                logger.info("Kokoro TTS audio generated", filename=filename)
                return filename
            else:
                logger.error("Kokoro TTS failed to generate audio")
                return None
                
        except Exception as e:
            logger.error("Kokoro TTS generation failed", error=str(e))
            return None
    
    async def _generate_with_liquidsoap(self, text: str, job_id: str) -> Optional[str]:
        """Generate audio using Liquidsoap's built-in TTS"""
        try:
            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"commentary_{job_id}_{timestamp}.wav"
            filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
            
            # Use espeak or festival for TTS (basic fallback)
            # In production, you'd want better quality TTS
            cmd = [
                "espeak",
                "-v", "en+f3",  # English female voice
                "-s", "160",    # Speed
                "-p", "50",     # Pitch
                "-g", "10",     # Gap between words
                "-w", filepath, # Output file
                clean_text
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(filepath):
                logger.info("Liquidsoap TTS audio generated", filepath=filepath)
                return filename
            else:
                logger.error("Liquidsoap TTS failed", stderr=stderr.decode())
                return None
        
        except Exception as e:
            logger.error("Liquidsoap TTS generation failed", error=str(e))
            return None
    
    async def _generate_with_xtts(self, text: str, job_id: str) -> Optional[str]:
        """Generate audio using XTTS server"""
        try:
            import httpx
            
            if not settings.XTTS_BASE_URL:
                logger.error("XTTS base URL not configured")
                return None
            
            # Clean text
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"commentary_{job_id}_{timestamp}.wav"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.XTTS_BASE_URL}/tts",
                    json={
                        "text": clean_text,
                        "voice": settings.XTTS_VOICE,
                        "language": "en",
                        "output_format": "wav"
                    }
                )
                
                if response.status_code == 200:
                    filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(response.content)
                    
                    logger.info("XTTS audio generated", filepath=filepath)
                    return filename
                else:
                    logger.error("XTTS request failed", status=response.status_code)
                    return None
        
        except Exception as e:
            logger.error("XTTS generation failed", error=str(e))
            return None