import os
import asyncio
import aiofiles
from typing import Optional
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
                # Fallback to XTTS if available
                try:
                    if getattr(settings, 'XTTS_BASE_URL', None):
                        xtts_voice = None
                        xtts_speaker = None
                        if dj_settings and isinstance(dj_settings, dict):
                            xtts_voice = dj_settings.get('xtts_voice') or dj_settings.get('dj_voice_id')
                            xtts_speaker = dj_settings.get('xtts_speaker') or dj_settings.get('dj_voice_speaker')
                        logger.warning("Kokoro failed; falling back to XTTS")
                        return await self._generate_with_xtts(text, job_id, voice_override=xtts_voice, speaker_override=xtts_speaker)
                except Exception:
                    pass
                return None
            elif provider == "liquidsoap":
                return await self._generate_with_liquidsoap(text, job_id)
            elif provider == "xtts":
                # Allow admin override for XTTS voice via 'xtts_voice' or generic 'dj_voice_id'
                xtts_voice = None
                xtts_speaker = None
                if dj_settings and isinstance(dj_settings, dict):
                    xtts_voice = dj_settings.get('xtts_voice') or dj_settings.get('dj_voice_id')
                    xtts_speaker = dj_settings.get('xtts_speaker') or dj_settings.get('dj_voice_speaker')
                primary = await self._generate_with_xtts(text, job_id, voice_override=xtts_voice, speaker_override=xtts_speaker)
                if primary:
                    return primary
                # Fallback to Kokoro if configured
                try:
                    logger.warning("XTTS failed; falling back to Kokoro")
                    return await self._generate_with_kokoro(text, job_id, voice_override=voice_override, speed_override=speed_override)
                except Exception:
                    return None
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
    
    async def _generate_with_xtts(self, text: str, job_id: str, voice_override: Optional[str] = None, speaker_override: Optional[str] = None) -> Optional[str]:
        """Generate audio using an XTTS-compatible server.

        Supports two API styles:
        1) JSON POST to `${XTTS_BASE_URL}/tts` with {text, voice, language, output_format}
        2) Query GET to `${XTTS_BASE_URL}/api/tts?text=...&voice=...` (OpenTTS)
        """
        try:
            import httpx

            base = (settings.XTTS_BASE_URL or '').rstrip('/')
            if not base:
                logger.error("XTTS base URL not configured")
                return None

            # Clean text
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            preferred_ext = 'mp3'
            filename = f"commentary_{job_id}_{timestamp}.{preferred_ext}"
            use_voice = voice_override or settings.XTTS_VOICE

            async with httpx.AsyncClient(timeout=45.0) as client:
                # Try JSON POST-style first
                response = None
                post_error = None
                try:
                    # Optional speaker parameter for multi-speaker voices
                    speaker = speaker_override
                    if not speaker:
                        try:
                            speaker = getattr(settings, 'XTTS_SPEAKER', None)
                        except Exception:
                            speaker = None
                    response = await client.post(
                        f"{base}/tts",
                        json={
                            "text": clean_text,
                            "voice": use_voice,
                            "language": "en",
                            "output_format": preferred_ext,
                            **({"speaker": speaker} if speaker else {}),
                        },
                    )
                except Exception as e_post:
                    post_error = e_post

                content: bytes = b""
                if response is not None and response.status_code == 200:
                    content = response.content
                else:
                    # Fallback to OpenTTS style GET /api/tts
                    try:
                        # Try GET with optional speaker param (OpenTTS style)
                        params = {
                            "voice": use_voice,
                            "text": clean_text,
                        }
                        # Add speaker if provided
                        if speaker_override:
                            params["speaker"] = speaker_override
                        else:
                            try:
                                sp = getattr(settings, 'XTTS_SPEAKER', None)
                                if sp:
                                    params["speaker"] = sp
                            except Exception:
                                pass
                        alt = await client.get(
                            f"{base}/api/tts",
                            params=params,
                        )
                        if alt.status_code == 200:
                            content = alt.content
                        else:
                            logger.error(
                                "XTTS request failed",
                                status=(response.status_code if response else None),
                                alt_status=alt.status_code,
                                post_error=(str(post_error) if post_error else None),
                            )
                            return None
                    except Exception as alt_err:
                        logger.error(
                            "XTTS requests failed",
                            post_error=(str(post_error) if post_error else None),
                            alt_error=str(alt_err),
                        )
                        return None

                # Save audio file
                filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(content)

                logger.info("XTTS audio generated", filepath=filepath)
                return filename

        except Exception as e:
            logger.error("XTTS generation failed", error=str(e))
            return None
    
    async def _generate_with_chatterbox(self, text: str, job_id: str, *, voice_override: Optional[str] = None, exaggeration_override: Optional[float] = None, cfg_weight_override: Optional[float] = None) -> Optional[str]:
        """Generate audio using Chatterbox TTS with OpenAI-compatible API."""
        try:
            import httpx

            base = (settings.CHATTERBOX_BASE_URL or '').rstrip('/')
            if not base:
                logger.error("Chatterbox base URL not configured")
                return None

            # Clean text for speech synthesis
            clean_text = text.replace('<speak>', '').replace('</speak>', '')
            clean_text = clean_text.replace('<break time="400ms"/>', ' ')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            preferred_ext = 'mp3'
            filename = f"commentary_{job_id}_{timestamp}.{preferred_ext}"
            
            # Use voice override or default
            use_voice = voice_override or settings.CHATTERBOX_VOICE
            use_exaggeration = exaggeration_override or settings.CHATTERBOX_EXAGGERATION
            use_cfg_weight = cfg_weight_override or settings.CHATTERBOX_CFG_WEIGHT

            async with httpx.AsyncClient(timeout=60.0) as client:
                # Use OpenAI-compatible endpoint
                response = await client.post(
                    f"{base}/v1/audio/speech",
                    json={
                        "model": "tts-1",
                        "input": clean_text,
                        "voice": use_voice,
                        "response_format": preferred_ext,
                        # Chatterbox-specific parameters
                        "exaggeration": use_exaggeration,
                        "cfg_weight": use_cfg_weight,
                    },
                )

                if response.status_code != 200:
                    logger.error("Chatterbox TTS request failed", status=response.status_code, text=response.text[:200])
                    return None

                # Save audio file
                filepath = os.path.join(settings.TTS_CACHE_DIR, filename)
                async with aiofiles.open(filepath, 'wb') as f:
                    await f.write(response.content)

                logger.info("Chatterbox TTS audio generated", 
                           filepath=filepath, 
                           voice=use_voice, 
                           exaggeration=use_exaggeration,
                           cfg_weight=use_cfg_weight)
                return filename

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
