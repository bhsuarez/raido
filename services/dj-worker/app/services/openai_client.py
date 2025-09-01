import asyncio
from typing import Optional
import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger()

class OpenAIClient:
    """Client for OpenAI API interactions"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required")
        
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_commentary(
        self, 
        prompt: str, 
        max_tokens: int = 200,
        temperature: float = 0.8
    ) -> Optional[str]:
        """Generate DJ commentary text using OpenAI"""
        try:
            logger.debug("Generating commentary with OpenAI", 
                        model=settings.OPENAI_MODEL,
                        max_tokens=max_tokens)
            
            response = await self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.5,  # Reduce repetition
                presence_penalty=0.3,   # Encourage variety
            )
            
            if response.choices:
                content = response.choices[0].message.content
                if content:
                    logger.debug("Generated commentary", 
                               length=len(content),
                               tokens_used=response.usage.total_tokens)
                    return content.strip()
            
            logger.warning("OpenAI returned empty response")
            return None
        
        except Exception as e:
            logger.error("OpenAI commentary generation failed", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)
    )
    async def generate_tts(
        self, 
        text: str,
        job_id: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ) -> Optional[bytes]:
        """Generate TTS audio using OpenAI"""
        try:
            voice = voice or settings.OPENAI_TTS_VOICE
            model = model or settings.OPENAI_TTS_MODEL
            
            logger.debug("Generating TTS with OpenAI", 
                        voice=voice, 
                        model=model, 
                        text_length=len(text))
            
            # Clean text for TTS (remove SSML tags)
            clean_text = self._clean_text_for_tts(text)
            
            response = await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=clean_text,
                response_format="mp3",
                speed=1.0
            )
            
            # Get the audio data
            audio_data = response.content
            
            logger.debug("Generated TTS audio", audio_size=len(audio_data))
            return audio_data
        
        except Exception as e:
            logger.error("OpenAI TTS generation failed", error=str(e))
            raise
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for TTS by removing SSML tags"""
        import re
        
        # Remove SSML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long (OpenAI TTS has limits)
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
            logger.warning("Text truncated for TTS", original_length=len(text))
        
        return text