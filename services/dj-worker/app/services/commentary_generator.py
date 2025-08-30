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
        
        # Default prompt template (will be overridden by database settings)
        self.prompt_template = self._load_default_prompt_template()
    
    def _load_default_prompt_template(self) -> Template:
        """Load the default DJ prompt template"""
        # Enhanced template with upcoming track focus and fact-based commentary
        template_text = """You're a pirate radio DJ introducing the NEXT song coming up. Create a brief 15-20 second intro for: "{{song_title}}" by {{artist}}{% if album %} from the album "{{album}}"{% endif %}{% if year %} ({{year}}){% endif %}. 

Share ONE interesting fact about the artist, song, or album. Be energetic, knowledgeable, and build excitement for what's coming up next. End with something like "Coming up next!" or "Here we go!" or "Let's dive in!"

Examples of good facts:
- Chart performance or awards
- Recording stories or collaborations  
- Cultural impact or covers by other artists
- Band member changes or solo careers
- Genre innovations or influences

Keep it conversational and exciting. No SSML tags needed.""".strip()
        
        return Template(template_text)

    def _load_prompt_template_from_settings(self, dj_settings: Dict[str, Any]) -> Template:
        """Load prompt template from settings or use default"""
        template_text = dj_settings.get('dj_prompt_template')
        if template_text and template_text.strip():
            logger.info("Using custom DJ prompt template", length=len(template_text))
            return Template(template_text)
        else:
            logger.info("Using default DJ prompt template")
            return self.prompt_template
    
    async def generate(self, track_info: Dict[str, Any], context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[Dict[str, str]]:
        """Generate DJ commentary for a track"""
        try:
            # Use provided settings or fall back to defaults
            if dj_settings is None:
                dj_settings = {}
            
            provider = dj_settings.get('dj_provider', settings.DJ_PROVIDER)
            logger.info("DJ commentary provider selected", provider=provider)
            
            # Check if commentary is disabled
            if provider == "disabled" or not dj_settings.get('enable_commentary', True):
                logger.info("DJ commentary is disabled")
                return None
            
            # Build prompt context
            prompt_context = self._build_prompt_context(track_info, context, dj_settings)
            
            # Generate commentary based on provider
            if provider == "openai" and self.openai_client and settings.OPENAI_API_KEY:
                return await self._generate_with_openai(prompt_context, dj_settings)
            elif provider == "ollama":
                return await self._generate_with_ollama(prompt_context, dj_settings)
            elif provider == "templates":
                return await self._generate_with_templates(prompt_context)
            else:
                logger.info("DJ provider not available", provider=provider, 
                           has_openai=bool(self.openai_client and settings.OPENAI_API_KEY))
                return None

        except Exception as e:
            logger.error("Failed to generate commentary", error=str(e))
            return None

    def _estimate_token_cap(self, dj_settings: Dict[str, Any]) -> int:
        """Estimate a safe token cap based on desired duration.

        Heuristic:
        - Average speaking rate ~ 2.5 words/sec (150 wpm)
        - Approx tokens per word ~ 1.3 (varies by model/language)
        - Cap tokens = seconds * 2.5 words/sec * 1.3 tokens/word
        """
        try:
            max_sec = int(dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS) or 0)
            if max_sec <= 0:
                return 200
            words = max_sec * 25 // 10  # 2.5 words/sec
            tokens = int(words * 1.3)
            # Keep within reasonable bounds
            return max(40, min(tokens, 300))
        except Exception:
            return 200

    def _trim_to_duration(self, text: str, dj_settings: Dict[str, Any]) -> str:
        """Trim commentary text to roughly fit max_seconds.

        Removes SSML to count words, trims at word boundary (preferring sentence end),
        and re-wraps with minimal SSML. This is a best-effort heuristic.
        """
        try:
            max_sec = int(dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS) or 0)
            if max_sec <= 0:
                return text

            # Allowed words at ~2.5 words/sec
            allowed_words = int(max_sec * 2.5)

            # Strip simple SSML for counting
            plain = text.replace('<speak>', '').replace('</speak>', '')
            plain = plain.replace('<break time=\"400ms\"/>', ' ').strip()

            words = plain.split()
            if len(words) <= allowed_words:
                return text

            # Trim to allowed words
            trimmed_words = words[:allowed_words]
            trimmed = ' '.join(trimmed_words)

            # Prefer to end at last sentence-ending punctuation within the trimmed region
            for punct in ['. ', '! ', '? ']:
                idx = trimmed.rfind(punct)
                if idx != -1 and idx > len(trimmed) * 0.6:  # avoid cutting too short
                    trimmed = trimmed[:idx + 1]
                    break

            # Re-wrap with minimal SSML like original
            return f"<speak><break time=\"400ms\"/>{trimmed.strip()}</speak>"
        except Exception:
            return text
    
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
            'play_index_in_block': 1,  # Could be enhanced to track position in commentary interval
            'total_songs_in_block': dj_settings.get('dj_commentary_interval', settings.DJ_COMMENTARY_INTERVAL),
            'recent_history': history_str,
            'up_next': up_next_str,
            'tone': dj_settings.get('dj_tone', settings.DJ_TONE),
            'profanity_filter': dj_settings.get('dj_profanity_filter', settings.DJ_PROFANITY_FILTER)
        }
    
    async def _generate_with_openai(self, prompt_context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[Dict[str, str]]:
        """Generate commentary using OpenAI"""
        try:
            # Get custom template if available
            template = self._load_prompt_template_from_settings(dj_settings or {})
            
            # Render the prompt
            prompt = template.render(**prompt_context)
            logger.info("Rendered DJ prompt (OpenAI)", preview=prompt[:160])
            
            # Use settings or defaults (cap by duration estimate)
            user_tokens = dj_settings.get('dj_max_tokens', 50) if dj_settings else 50
            est_cap = self._estimate_token_cap(dj_settings or {})
            max_tokens = min(int(user_tokens), est_cap)
            temperature = dj_settings.get('dj_temperature', 0.8) if dj_settings else 0.8
            
            # Call OpenAI with custom parameters
            response = await self.openai_client.generate_commentary(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if response:
                # Clean up the response (remove SSML tags for now, add them back if needed)
                cleaned = response.strip()
                if cleaned.startswith('<speak>'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('</speak>'):
                    cleaned = cleaned[:-8]
                full_transcript = cleaned.strip()

                # Add basic SSML structure and trim for timing
                ssml = f'<speak><break time=\"400ms\"/>{full_transcript}</speak>'
                trimmed_ssml = self._trim_to_duration(ssml, dj_settings or {})
                return {"ssml": trimmed_ssml, "transcript_full": full_transcript}
            
            return None
        
        except Exception as e:
            logger.error("OpenAI commentary generation failed", error=str(e))
            return None
    
    async def _generate_with_ollama(self, prompt_context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[Dict[str, str]]:
        """Generate commentary using Ollama"""
        try:
            # Get custom template if available
            template = self._load_prompt_template_from_settings(dj_settings or {})
            
            # Render the prompt
            prompt = template.render(**prompt_context)
            logger.info("Rendered DJ prompt (Ollama)", preview=prompt[:160])
            
            # Use settings or defaults (cap by duration estimate)
            user_tokens = dj_settings.get('dj_max_tokens', 200) if dj_settings else 200
            est_cap = self._estimate_token_cap(dj_settings or {})
            max_tokens = min(int(user_tokens), est_cap)
            temperature = dj_settings.get('dj_temperature', 0.8) if dj_settings else 0.8
            model = dj_settings.get('dj_model', settings.OLLAMA_MODEL) if dj_settings else settings.OLLAMA_MODEL
            
            # Call Ollama with custom parameters
            response = await self.ollama_client.generate_commentary(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model
            )
            
            if response:
                # Clean and format response
                full_transcript = response.strip()
                ssml = f'<speak><break time=\"400ms\"/>{full_transcript}</speak>'
                # Heuristic trim to fit duration
                trimmed_ssml = self._trim_to_duration(ssml, dj_settings or {})
                return {"ssml": trimmed_ssml, "transcript_full": full_transcript}
            
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e))
            return None

    async def _generate_with_templates(self, prompt_context: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Generate commentary using pre-written templates (fast fallback)"""
        try:
            import random
            
            # Pre-written DJ commentary templates for upcoming tracks
            templates = [
                "Ahoy there, mateys! Coming up next, we've got {artist} with {song_title}. This one's gonna be epic!",
                "All hands on deck! Next up is {artist} bringing you {song_title}. Get ready to rock!",
                "Sailing into our next treasure - {artist} and {song_title}. You're gonna love this one!",
                "From the crow's nest, I can see our next adventure: {artist} with {song_title}. Coming up!",
                "Batten down the hatches! {artist}'s {song_title} is next on the horizon!",
                "Yo ho ho! Next up we've got {artist} with {song_title}. This one's pure gold!",
                "Set your compass for this beauty coming next - {artist} performing {song_title}!",
                "Captain's choice for our next voyage: {song_title} by {artist}. Here we go!",
                "Smooth sailing continues with {artist} and {song_title} coming up next. Ahoy!",
                "Next up from the radio galley - {artist} with {song_title}. Don't touch that dial!"
            ]
            
            # Select random template and format it
            template = random.choice(templates)
            commentary = template.format(
                artist=prompt_context.get('artist', 'Unknown Artist'),
                song_title=prompt_context.get('song_title', 'Unknown Title')
            )
            
            # Add SSML structure and also return full transcript
            return {"ssml": f'<speak><break time=\"400ms\"/>{commentary}</speak>', "transcript_full": commentary}
            
        except Exception as e:
            logger.error("Template commentary generation failed", error=str(e))
            return None
