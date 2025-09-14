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

    def _sanitize_generated_text(self, text: str) -> str:
        """Remove stage directions, SSML and parenthetical asides.

        Heuristics:
        - Strip SSML tags if any slipped in
        - Drop anything inside () or []
        - Remove leading/trailing quotes
        - Collapse whitespace
        """
        import re

        if not text:
            return text

        # Remove SSML and HTML-like tags
        cleaned = re.sub(r"<[^>]+>", "", text)

        # Remove bracketed/parenthetical content entirely
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)

        # Remove asterisks stage directions like *applause*
        cleaned = re.sub(r"\*[^*]+\*", "", cleaned)

        # Strip leading/trailing quotes
        cleaned = cleaned.strip().strip('\"\'')

        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Fix common tokenization artifacts from streaming (e.g., Llama):
        # - Space before apostrophes in contractions: We ' re -> We're
        cleaned = re.sub(r"\b(\w+)\s+'\s+(s|re|ve|ll|d|m|t)\b", r"\1'\2", cleaned, flags=re.IGNORECASE)
        # - Extra spaces before punctuation like , . ! ?
        cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
        # - Ensure space after sentence-ending punctuation if followed immediately by a letter
        cleaned = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", cleaned)
        return cleaned
    
    def _is_using_chatterbox_tts(self, dj_settings: Dict[str, Any] = None) -> bool:
        """Check if Chatterbox TTS is being used"""
        if dj_settings:
            voice_provider = dj_settings.get('dj_voice_provider')
            if voice_provider == "chatterbox":
                return True
            # If dj_settings are provided but don't specify chatterbox, return False
            # Don't fall back to env settings when we have API settings
            return False
        return settings.DJ_VOICE_PROVIDER == "chatterbox"

    async def generate(self, track_info: Dict[str, Any], context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[Dict[str, str]]:
        """Generate DJ commentary for a track"""
        try:
            # Use provided settings or fall back to defaults
            if dj_settings is None:
                dj_settings = {}
            
            # Use API settings first, fall back to env only if no API settings provided
            if dj_settings:
                provider = dj_settings.get('dj_provider', settings.DJ_PROVIDER)
            else:
                provider = settings.DJ_PROVIDER
            logger.info("DJ commentary provider selected", provider=provider)
            
            # Check if commentary is disabled
            if provider == "disabled" or not dj_settings.get('enable_commentary', True):
                logger.info("DJ commentary is disabled")
                return None
            
            # Build prompt context
            prompt_context = self._build_prompt_context(track_info, context, dj_settings)
            
            # If using Chatterbox TTS, modify settings for shorter output
            if self._is_using_chatterbox_tts(dj_settings):
                dj_settings = dj_settings.copy()  # Don't modify original
                # Reduce max seconds for Chatterbox to keep synthesis manageable
                current_max = dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS)
                dj_settings['dj_max_seconds'] = min(current_max, 15)  # Cap at 15 seconds
                logger.info("Adjusted max_seconds for Chatterbox TTS", max_seconds=dj_settings['dj_max_seconds'])
            
            # Generate commentary based on provider
            if provider == "openai" and self.openai_client and settings.OPENAI_API_KEY:
                return await self._generate_with_openai(prompt_context, dj_settings)
            elif provider == "ollama":
                result = await self._generate_with_ollama(prompt_context, dj_settings)
                if result:
                    return result
                # Safety fallback: if Ollama fails, use templates to keep TTS flowing
                logger.warning("Ollama failed; falling back to templates provider for this job")
                return await self._generate_with_templates(prompt_context)
            elif provider == "templates":
                return await self._generate_with_templates(prompt_context, dj_settings)
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
        - Average speaking rate ~ 3.5 words/sec (210 wpm)
        - Approx tokens per word ~ 1.3 (varies by model/language)
        - Cap tokens = seconds * 3.5 words/sec * 1.3 tokens/word
        """
        try:
            max_sec = int(dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS) or 0)
            if max_sec <= 0:
                return 200
            words = max_sec * 35 // 10  # 3.5 words/sec
            tokens = int(words * 1.3)
            # Keep within reasonable bounds
            return max(40, min(tokens, 300))
        except Exception:
            return 200

    def _trim_to_duration(self, text: str, dj_settings: Dict[str, Any]) -> str:
        """Trim commentary text to roughly fit max_seconds with natural sentence endings.

        Heuristics:
        - Estimate allowed words by max_seconds (~2.5 wps baseline).
        - Prefer cutting at a sentence boundary near the target window.
        - If no boundary behind target, look slightly ahead (up to +20% words).
        - As a last resort, append a period to avoid abrupt cutoff.
        """
        try:
            max_sec = int(dj_settings.get('dj_max_seconds', settings.DJ_MAX_SECONDS) or 0)
            if max_sec <= 0:
                return text

            # Allowed words at ~3.5 words/sec (more realistic for DJ commentary)
            words_per_sec = 3.5
            allowed_words = max(1, int(max_sec * words_per_sec))

            # Strip simple SSML for counting/segmenting
            plain = text.replace('<speak>', '').replace('</speak>', '')
            plain = plain.replace('<break time=\"400ms\"/>', ' ').strip()

            words = plain.split()
            if len(words) <= allowed_words:
                return text

            # Hard stop limit: allow up to +20% when scanning forward for punctuation
            forward_limit = int(allowed_words * 1.2)
            forward_limit = min(forward_limit, len(words))

            # Compose candidate segments
            target_segment = ' '.join(words[:allowed_words])
            forward_segment = ' '.join(words[:forward_limit])

            def cut_on_punct(s: str) -> str:
                for punct in ['. ', '! ', '? ']:
                    idx = s.rfind(punct)
                    if idx != -1 and idx > len(s) * 0.5:  # avoid cutting too short
                        return s[:idx + 1]
                return s

            # Prefer to end within the target window
            trimmed = cut_on_punct(target_segment)

            # If no good boundary found inside target, scan slightly ahead for a boundary
            if trimmed == target_segment or not trimmed.endswith(('.', '!', '?')):
                ahead = cut_on_punct(forward_segment)
                if ahead.endswith(('.', '!', '?')):
                    trimmed = ahead

            trimmed = trimmed.strip()
            if not trimmed.endswith(('.', '!', '?')):
                # Ensure a graceful stop
                trimmed = trimmed.rstrip(',;:') + '.'

            # Re-wrap with minimal SSML like original
            return f"<speak><break time=\"400ms\"/>{trimmed}</speak>"
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
                # Clean up the response and enforce no stage directions
                cleaned = response.strip()
                if cleaned.startswith('<speak>'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('</speak>'):
                    cleaned = cleaned[:-8]
                full_transcript = self._sanitize_generated_text(cleaned.strip())

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
                # Clean and format response; enforce no stage directions
                full_transcript = self._sanitize_generated_text(response.strip())
                ssml = f'<speak><break time=\"400ms\"/>{full_transcript}</speak>'
                # Heuristic trim to fit duration
                trimmed_ssml = self._trim_to_duration(ssml, dj_settings or {})
                mode = None
                try:
                    mode = getattr(self.ollama_client, 'last_mode', None)
                except Exception:
                    mode = None
                return {"ssml": trimmed_ssml, "transcript_full": full_transcript, "gen_mode": mode}
            
            return None
        
        except Exception as e:
            logger.error("Ollama commentary generation failed", error=str(e))
            return None

    async def _generate_with_templates(self, prompt_context: Dict[str, Any], dj_settings: Dict[str, Any] = None) -> Optional[Dict[str, str]]:
        """Generate commentary using pre-written templates (fast fallback)"""
        try:
            import random
            
            # Check if we should use shorter templates for Chatterbox
            is_chatterbox = self._is_using_chatterbox_tts(dj_settings)
            
            if is_chatterbox:
                # Shorter templates optimized for Chatterbox TTS
                templates = [
                    "Next up, {artist} with {song_title}!",
                    "Coming up: {song_title} by {artist}!",
                    "Here's {artist} with {song_title}!",
                    "Up next, {artist} and {song_title}!",
                    "Now playing {song_title} by {artist}!",
                    "{artist} with {song_title} coming up!",
                    "Next: {song_title} from {artist}!",
                    "Here we go with {artist}!"
                ]
            else:
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
