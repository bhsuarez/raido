import asyncio
from typing import Dict, Any, Optional
import structlog
from jinja2 import Template
from datetime import datetime

from app.core.config import settings
from app.services.openai_client import OpenAIClient
from app.services.ollama_client import OllamaClient

logger = structlog.get_logger()

class CommentaryGenerator:
    """Generates DJ commentary using various AI providers"""
    
    def __init__(self):
        self.openai_client = OpenAIClient() if settings.OPENAI_API_KEY else None
        self.ollama_client = OllamaClient()
        
        # Load DJ prompt template
        self.prompt_template = self._load_prompt_template()
    
    def _load_prompt_template(self) -> Template:
        """Load the DJ prompt template"""
        # This could be loaded from a file or database
        template_text = """You're a pirate radio DJ. Write a brief 10-15 second intro for: "{{song_title}}" by {{artist}}. Be energetic and concise. End with "Let's go!" or similar. No SSML tags needed.""".strip()
        
        return Template(template_text)
    
    async def generate(self, track_info: Dict[str, Any], context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[str]:
        """Generate DJ commentary for a track"""
        try:
            # Use provided settings or fall back to defaults
            if dj_settings is None:
                dj_settings = {}
            
            provider = dj_settings.get('dj_provider', settings.DJ_PROVIDER)
            
            # Check if commentary is disabled
            if provider == "disabled" or not dj_settings.get('enable_commentary', True):
                logger.info("DJ commentary is disabled")
                return None
            
            # Build prompt context
            prompt_context = self._build_prompt_context(track_info, context, dj_settings)
            
            # Generate commentary based on provider
            if provider == "openai" and self.openai_client and settings.OPENAI_API_KEY:
                return await self._generate_with_openai(prompt_context)
            elif provider == "ollama":
                return await self._generate_with_ollama(prompt_context)
            else:
                logger.info("DJ provider not available", provider=provider, 
                           has_openai=bool(self.openai_client and settings.OPENAI_API_KEY))
                return None
        
        except Exception as e:
            logger.error("Failed to generate commentary", error=str(e))
            return None
    
    def _build_prompt_context(self, track_info: Dict[str, Any], context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build context for the prompt template"""
        
        # Format recent history
        recent_history = context.get('recent_history', [])
        history_str = ', '.join(recent_history[:3]) if recent_history else "None"
        
        # Format upcoming tracks
        up_next = context.get('up_next', [])
        up_next_str = ', '.join(up_next[:2]) if up_next else "None"
        
        if dj_settings is None:
            dj_settings = {}
            
        return {
            'station_name': dj_settings.get('station_name', settings.STATION_NAME),
            'max_seconds': dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS),
            'song_title': track_info.get('title', 'Unknown Title'),
            'artist': track_info.get('artist', 'Unknown Artist'),
            'album': track_info.get('album', 'Unknown Album'),
            'year': track_info.get('year', 'Unknown'),
            'genre': track_info.get('genre', 'Various'),
            'duration_sec': int(track_info.get('duration_sec', 0)) if track_info.get('duration_sec') else 'Unknown',
            'play_index_in_block': 1,  # TODO: Calculate based on recent commentary
            'total_songs_in_block': dj_settings.get('dj_commentary_interval', settings.DJ_COMMENTARY_INTERVAL),
            'recent_history': history_str,
            'up_next': up_next_str,
            'tone': dj_settings.get('dj_tone', settings.DJ_TONE),
            'profanity_filter': dj_settings.get('dj_profanity_filter', settings.DJ_PROFANITY_FILTER)
        }
    
    async def _generate_with_openai(self, prompt_context: Dict[str, Any]) -> Optional[str]:
        """Generate commentary using OpenAI"""
        try:
            # Render the prompt
            prompt = self.prompt_template.render(**prompt_context)
            
            # Call OpenAI with shorter token limit
            response = await self.openai_client.generate_commentary(
                prompt=prompt,
                max_tokens=50,
                temperature=0.8
            )
            
            if response:
                # Clean up the response (remove SSML tags for now, add them back if needed)
                cleaned = response.strip()
                if cleaned.startswith('<speak>'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('</speak>'):
                    cleaned = cleaned[:-8]
                
                # Add basic SSML structure
                return f'<speak><break time="400ms"/>{cleaned.strip()}</speak>'
            
            return None
        
        except Exception as e:
            logger.error("OpenAI commentary generation failed", error=str(e))
            return None
    
    async def _generate_with_ollama(self, prompt_context: Dict[str, Any]) -> Optional[str]:
        """Generate commentary using Ollama"""
        try:
            # Render the prompt
            prompt = self.prompt_template.render(**prompt_context)
            
            # Call Ollama
            response = await self.ollama_client.generate_commentary(
                prompt=prompt,
                max_tokens=200,
                temperature=0.8
            )
            
            if response:
                # Clean and format response
                cleaned = response.strip()
                return f'<speak><break time="400ms"/>{cleaned}</speak>'
            
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e))
            return None