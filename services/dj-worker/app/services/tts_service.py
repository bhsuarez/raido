import os
import asyncio
import aiofiles
from typing import Optional, Tuple
import structlog
from datetime import datetime

from app.core.config import settings
from app.services.kokoro_client import KokoroClient
from app.services.openai_client import OpenAIClient

logger = structlog.get_logger()

class TTSService:
    """Text-to-Speech service with multiple provider support"""
    
    def __init__(self):
        self.kokoro_client = KokoroClient()
        self._openai_client = None  # Lazy initialization
        
        # Try to ensure TTS cache directory exists
        try:
            os.makedirs(settings.TTS_CACHE_DIR, exist_ok=True)
            logger.info("TTS cache directory ready", dir=settings.TTS_CACHE_DIR)
        except PermissionError as e:
            logger.error("Cannot create TTS cache directory", dir=settings.TTS_CACHE_DIR, error=str(e))
            raise
    
    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self._openai_client is None:
            self._openai_client = OpenAIClient()
        return self._openai_client
    
    async def generate_audio(self, text: str, job_id: str, dj_settings: Optional[dict] = None) -> Optional[str]:
        """Generate audio from text using the configured TTS provider.

        Prefers per-job admin setting (dj_voice_provider) when provided,
        falling back to the environment default.
        """
        try:
            # Prefer dynamic admin setting if present, otherwise fallback to env default
            provider = (
                (dj_settings.get('dj_voice_provider') if isinstance(dj_settings, dict) else None)
                or settings.DJ_VOICE_PROVIDER
            )
            voice_override = None
            speed_override = None
            if dj_settings:
                voice_override = dj_settings.get('kokoro_voice') or dj_settings.get('dj_voice_id')
                # Optional speed field if present in settings
                speed_val = dj_settings.get('kokoro_speed') if isinstance(dj_settings, dict) else None
                try:
                    if speed_val is not None:
                        speed_override = float(speed_val)
                except Exception:
                    speed_override = None
            
            # Primary path
            if provider == "kokoro":
                primary = await self._generate_with_kokoro(text, job_id, voice_override=voice_override, speed_override=speed_override)
                if primary:
                    return primary
                return None
            elif provider == "liquidsoap":
                return await self._generate_with_liquidsoap(text, job_id)
            elif provider == "openai_tts":
                # Allow admin override for OpenAI TTS voice via 'openai_tts_voice' or generic 'dj_voice_id'
                openai_voice = None
                if dj_settings and isinstance(dj_settings, dict):
                    openai_voice = dj_settings.get('openai_tts_voice') or dj_settings.get('dj_voice_id')
                primary = await self._generate_with_openai_tts(text, job_id, voice_override=openai_voice)
                if primary:
                    return primary
                # Fallback to Kokoro if configured
                try:
                    logger.warning("OpenAI TTS failed; falling back to Kokoro")
                    return await self._generate_with_kokoro(text, job_id, voice_override=voice_override, speed_override=speed_override)
                except Exception:
                    return None
            elif provider == "chatterbox":
                # Allow admin override for Chatterbox voice via 'chatterbox_voice' or generic 'dj_voice_id'
                chatterbox_voice = None
                chatterbox_exaggeration = None
                chatterbox_cfg_weight = None
                if dj_settings and isinstance(dj_settings, dict):
                    chatterbox_voice = dj_settings.get('chatterbox_voice') or dj_settings.get('dj_voice_id')
                    try:
                        chatterbox_exaggeration = float(dj_settings.get('chatterbox_exaggeration', 1.0))
                    except Exception:
                        chatterbox_exaggeration = None
                    try:
                        chatterbox_cfg_weight = float(dj_settings.get('chatterbox_cfg_weight', 0.5))
                    except Exception:
                        chatterbox_cfg_weight = None
                primary = await self._generate_with_chatterbox(text, job_id, voice_override=chatterbox_voice, exaggeration_override=chatterbox_exaggeration, cfg_weight_override=chatterbox_cfg_weight)
                if primary:
                    return primary
                # Fallback to Kokoro if configured
                try:
                    logger.warning("Chatterbox failed; falling back to Kokoro")
                    return await self._generate_with_kokoro(text, job_id, voice_override=voice_override, speed_override=speed_override)
                except Exception:
                    return None
            else:
                logger.error("No valid TTS provider configured", provider=provider)
                return None
        
        except Exception as e:
            logger.error("TTS generation failed", error=str(e), provider=provider)
            return None
    
    
    async def _generate_with_kokoro(self, text: str, job_id: str, *, voice_override: Optional[str] = None, speed_override: Optional[float] = None) -> Optional[str]:
        """Generate audio using Kokoro TTS"""
        try:
            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')
            
            filename = await self.kokoro_client.generate_audio(clean_text, job_id, voice=voice_override, speed=speed_override)
            
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
    
    
    async def _generate_with_chatterbox(self, text: str, job_id: str, *, voice_override: Optional[str] = None, exaggeration_override: Optional[float] = None, cfg_weight_override: Optional[float] = None) -> Optional[str]:
        """Generate audio using Chatterbox TTS without voice cloning."""
        try:
            import httpx

            def _sniff_audio_extension(data: bytes, content_type: Optional[str] = None) -> Tuple[str, str]:
                ct = (content_type or "").lower()
                head = data[:16] if data else b""
                try:
                    if head.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
                        return ("wav", "audio/wav")
                    # MP3: ID3 tag or MPEG sync (11111111 111xxxxx)
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

            base = (settings.CHATTERBOX_BASE_URL or '').rstrip('/')
            if not base:
                logger.error("Chatterbox base URL not configured")
                return None

            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Use voice override or default
            use_voice = voice_override or settings.CHATTERBOX_VOICE
            use_exaggeration = exaggeration_override or settings.CHATTERBOX_EXAGGERATION
            use_cfg_weight = cfg_weight_override or settings.CHATTERBOX_CFG_WEIGHT

            async with httpx.AsyncClient(timeout=settings.CHATTERBOX_TTS_TIMEOUT) as client:
                # Use new chatterbox-shim API endpoint
                try:
                    url = f"{base}/api/speak"
                    payload = {
                        "text": clean_text,
                        "voice_id": use_voice or "default"
                    }

                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200 and resp.content:
                        # Validate audio content
                        ct = (resp.headers.get("content-type", "") or "").lower()
                        content = resp.content or b""
                        ext, sniffed_mime = _sniff_audio_extension(content, ct)
                        looks_audio = ext in ("mp3", "wav", "ogg", "flac") and len(content) > 1000

                        if looks_audio:
                            filename = f"commentary_{job_id}_{timestamp}.{ext}"
                            filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
                            async with aiofiles.open(filepath, 'wb') as f:
                                await f.write(content)
                            if sniffed_mime and ct and sniffed_mime != ct:
                                logger.warning("MIME/content-type mismatch from Chatterbox", sniffed=sniffed_mime, header=ct, filename=filename)
                            logger.info("Chatterbox TTS audio generated", filepath=filepath, text_length=len(clean_text))
                            return filename
                        else:
                            logger.error("Chatterbox returned non-audio content", preview=(content[:120].decode(errors='ignore') if content else ""))
                            return None
                    else:
                        logger.warning("Chatterbox /api/speak failed", status=resp.status_code, text=resp.text[:200])
                except Exception as e:
                    logger.warning("Chatterbox /api/speak error", error=str(e))

                # No legacy or cloning-based fallbacks; only support standard API

        except Exception as e:
            logger.error("Chatterbox TTS generation failed", error=str(e))
            return None

    async def _generate_with_openai_tts(self, text: str, job_id: str, *, voice_override: Optional[str] = None) -> Optional[str]:
        """Generate audio using OpenAI TTS"""
        try:
            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')
            
            # Use OpenAI client to generate audio
            audio_data = await self.openai_client.generate_tts(clean_text, job_id, voice=voice_override)
            
            if audio_data:
                # Save the audio data to file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"commentary_{job_id}_{timestamp}.mp3"
                filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
                
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(audio_data)
                
                logger.info("OpenAI TTS audio generated", filename=filename, voice=voice_override)
                return filename
            else:
                logger.error("OpenAI TTS failed to generate audio")
                return None
                
        except Exception as e:
            logger.error("OpenAI TTS generation failed", error=str(e))
            return None
