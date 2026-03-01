import asyncio
import os
import time
from typing import Optional, Dict, Any
import structlog
from datetime import datetime, timezone

from app.core.config import settings
from app.services.commentary_generator import CommentaryGenerator
from app.services.tts_service import TTSService
from app.services.api_client import APIClient
from app.services.system_monitor import system_monitor
from app.models.commentary_job import CommentaryJob, JobStatus

logger = structlog.get_logger()

class DJWorker:
    """Main DJ Worker that processes commentary generation jobs"""
    
    def __init__(
        self, 
        commentary_generator: CommentaryGenerator,
        tts_service: TTSService
    ):
        self.commentary_generator = commentary_generator
        self.tts_service = tts_service
        self.api_client = APIClient(settings.API_BASE_URL)
        
        self.is_running = False
        self.current_jobs: Dict[int, CommentaryJob] = {}
        self.job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)
        # Track recent intros by upcoming track id to avoid duplicates
        # Maps track_id -> unix timestamp of when an intro was generated
        self._recent_intros: Dict[int, float] = {}
        # Track in-flight placeholder commentary IDs per track to avoid duplicates
        # Maps track_id -> commentary_id (running)
        self._placeholders: Dict[int, int] = {}
    
    async def run(self):
        """Main worker loop with system health monitoring"""
        self.is_running = True
        logger.info("🎙️ DJ Worker started")
        # Best-effort warmup of Ollama to reduce first-request latency
        try:
            if hasattr(self.commentary_generator, 'ollama_client'):
                await self.commentary_generator.ollama_client.warmup()
        except Exception:
            pass
        
        # Schedule periodic system health monitoring
        health_monitor_task = asyncio.create_task(self._periodic_health_monitoring())
        
        try:
            while self.is_running:
                logger.info("🔄 DJ Worker polling for jobs...")
                await self._process_pending_jobs()
                logger.info(f"💤 Sleeping for {settings.WORKER_POLL_INTERVAL} seconds")
                await asyncio.sleep(settings.WORKER_POLL_INTERVAL)
        
        except asyncio.CancelledError:
            logger.info("DJ Worker cancelled")
        except Exception as e:
            logger.error("Unexpected error in worker loop", error=str(e))
        finally:
            self.is_running = False
            health_monitor_task.cancel()
    
    async def _periodic_health_monitoring(self):
        """Periodic system health monitoring task"""
        while self.is_running:
            try:
                if system_monitor:
                    system_health = await system_monitor.check_system_health()
                    # System protection removed since heavy services run externally
                    if False:  # Disabled protection check
                        logger.warning("System protection is active - limiting operations")
                    
                    # Log system info periodically
                    system_info = await system_monitor.get_system_info()
                    logger.debug("System health check", 
                               cpu=system_info.get('cpu', {}),
                               memory=system_info.get('memory', {}))
                else:
                    logger.debug("System monitoring disabled")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(60)
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info("Stopping DJ Worker...")
        self.is_running = False
        
        # Wait for current jobs to complete
        if self.current_jobs:
            logger.info(f"Waiting for {len(self.current_jobs)} jobs to complete...")
            await asyncio.sleep(5)  # Give jobs time to finish
    
    async def _cleanup_stale_placeholders(self):
        """Mark running commentaries as failed if they've been stuck for > 3 minutes."""
        import time as _time
        stale_cutoff = 180  # seconds
        now = _time.time()
        stale_ids = [
            tid for tid, cid in list(self._placeholders.items())
            # We don't have a per-placeholder start time, so use _recent_intros as proxy;
            # if the track_id is NOT in _recent_intros (i.e. never finished), check via API
        ]
        # Clean up any in-memory placeholder for tracks that were registered > 3 min ago
        # We use a separate _placeholder_times dict for this
        if not hasattr(self, '_placeholder_times'):
            self._placeholder_times: dict = {}
        for tid in list(self._placeholders.keys()):
            started = self._placeholder_times.get(tid, now - stale_cutoff - 1)
            if now - started > stale_cutoff:
                cid = self._placeholders.pop(tid, None)
                self._placeholder_times.pop(tid, None)
                if cid:
                    try:
                        await self.api_client.update_commentary(cid, {
                            'status': 'failed',
                            'error_message': 'Timed out after 3 minutes',
                        })
                        logger.warning("Marked stale placeholder as failed", commentary_id=cid, track_id=tid)
                    except Exception as e:
                        logger.warning("Could not mark stale placeholder as failed", error=str(e))


    async def _process_pending_jobs(self):
        """Check for and process pending commentary jobs"""
        try:
            # Clean up any placeholder commentaries stuck in 'running' longer than 3 minutes
            await self._cleanup_stale_placeholders()

            logger.info("📊 Checking if commentary should be generated...")
            # Check if we need to generate commentary based on current track timing
            should_generate = await self._should_generate_commentary()
            logger.info(f"🎯 Should generate commentary: {should_generate}")
            
            if should_generate:
                logger.info("🎵 Getting next track for commentary...")
                # Get the next upcoming track to generate commentary for
                next_track = await self._get_next_track_for_commentary()
                logger.info(f"📀 Next track found: {next_track is not None}")
                
                if next_track and next_track.get('track'):
                    logger.info(f"🎤 Processing track: {next_track['track'].get('title')} by {next_track['track'].get('artist')}")
                    job = CommentaryJob(
                        track_info=next_track['track'],
                        play_info=None,  # No play record yet for upcoming track
                        context=await self._build_context()
                    )
                    
                    # Process the job
                    await self._process_job(job)
                else:
                    logger.info("❌ No valid track found for commentary")
        
        except Exception as e:
            logger.error("Error processing pending jobs", error=str(e))
    
    async def _should_generate_commentary(self) -> bool:
        """Determine if commentary should be generated for next track"""
        try:
            # Load settings first to respect admin selections over env defaults
            settings_response = await self.api_client.get_settings(station=settings.STATION_NAME)
            if not settings_response:
                return False

            provider = settings_response.get('dj_provider', settings.DJ_PROVIDER)
            enabled = settings_response.get('enable_commentary', True)

            # Respect admin-enabled flag and provider selection
            if not enabled or provider == "disabled":
                return False

            # CRITICAL: Check system health before proceeding
            if system_monitor:
                system_health = await system_monitor.check_system_health()
                if not system_health.is_healthy:
                    logger.warning("Skipping commentary generation due to system health", 
                                 warnings=system_health.warnings,
                                 cpu=system_health.cpu_percent,
                                 memory=system_health.memory_percent)
                    return False
                
            # Determine commentary interval
            interval = int(settings_response.get('dj_commentary_interval', 1))
            
            # Get current playing track info to determine timing
            now_playing = await self.api_client.get_now_playing()
            # Backend returns: { is_playing: bool, track: {}, play: {}, progress: {} }
            if not now_playing or not now_playing.get('track'):
                return False
            
            # Check if we should generate commentary based on interval
            # Generate commentary every N tracks
            recent_history = await self.api_client.get_history(limit=interval + 1)
            if not recent_history or 'tracks' not in recent_history:
                return True  # Default to generating if we can't check history
            
            tracks_since_commentary = 0
            for track_play in recent_history['tracks']:
                if track_play.get('commentary'):
                    break  # Found the last commentary
                tracks_since_commentary += 1
            
            # Generate commentary if we've played enough tracks since last commentary
            return tracks_since_commentary >= interval
        
        except Exception as e:
            logger.error("Error checking if commentary should be generated", error=str(e))
            return False
    
    async def _get_next_track_for_commentary(self) -> Optional[Dict[str, Any]]:
        """Get the next upcoming track that needs commentary"""
        try:
            logger.info("🔍 Fetching next up tracks from API...")
            # Get upcoming tracks
            next_up = await self.api_client.get_next_up()
            logger.info(f"📡 API response received: {next_up is not None}")
            if not next_up or 'next_tracks' not in next_up:
                logger.info("❌ No next_tracks found in API response")
                return None
            
            logger.info(f"🎵 Found {len(next_up['next_tracks'])} upcoming tracks")
            # Get the first upcoming track that doesn't have commentary prepared
            for next_track in next_up['next_tracks'][:1]:  # Just check the very next track
                track = next_track.get('track')
                logger.info(f"🎶 Track found: {track is not None}")
                if track:
                    logger.info(f"🏷️ Track details: ID={track.get('id')}, Title='{track.get('title')}', Artist='{track.get('artist')}'")
                    # Check if this track already has recent commentary prepared
                    # (to avoid generating multiple commentaries for the same track)
                    track_id = track.get('id')
                    logger.info(f"🆔 Track ID: {track_id}")

                    # Skip tracks with invalid metadata (ID 0, Unknown Artist, etc.)
                    if (track_id is None or track_id == 0 or
                        track.get('title') in ['Unknown', ''] or
                        track.get('artist') in ['Unknown Artist', 'Unknown', '']):
                        logger.info("❌ Track skipped (invalid metadata: ID=0 or Unknown)")
                        continue

                    has_recent = await self._has_recent_commentary(track_id)
                    logger.info(f"⏰ Has recent commentary: {has_recent}")
                    if not has_recent:
                        logger.info("✅ Track selected for commentary")
                        return next_track
                    else:
                        logger.info("❌ Track skipped (has recent commentary)")
            
            return None
        
        except Exception as e:
            logger.error("Error getting next track for commentary", error=str(e))
            return None
    
    async def _has_recent_commentary(self, track_id: int) -> bool:
        """Check if a track recently had commentary to avoid duplicates.

        Uses a small in-memory cache and falls back to the API's
        /api/v1/now/history endpoint to look for recent commentary entries
        matching the given track_id.
        """
        try:
            import time as _time
            now = _time.time()

            # Use minutes window based on DJ_COMMENTARY_INTERVAL (tracks setting reused as a time guard)
            interval_minutes = getattr(settings, 'DJ_COMMENTARY_INTERVAL', 5)
            # Ensure a reasonable minimum dedup window (5 minutes)
            cutoff_seconds = max(300, int(interval_minutes) * 60)
            cutoff = now - cutoff_seconds

            # Prune very old entries from in-memory cache
            self._recent_intros = {tid: ts for tid, ts in self._recent_intros.items() if ts >= cutoff}

            # First check in-memory cache for recent entries
            last = self._recent_intros.get(track_id)
            if last and last >= cutoff:
                return True

            # Check if there's already a TTS generation in progress for this track
            if track_id in self._placeholders:
                logger.info(f"🎵 TTS already generating for track {track_id}")
                return True

            # Check recent history via API for commentary on this specific track
            try:
                from datetime import datetime, timezone
                hist = await self.api_client.get_history(limit=20)
                if hist and isinstance(hist, dict):
                    items = hist.get('tracks') or []
                    for item in items:
                        t = (item or {}).get('track') or {}
                        com = (item or {}).get('commentary') or None
                        # Match by track id and ensure commentary is recent
                        if int(t.get('id') or 0) == int(track_id) and com:
                            # Parse created_at if present; otherwise assume "recent enough"
                            created_at = com.get('created_at') if isinstance(com, dict) else None
                            if created_at:
                                try:
                                    # created_at is ISO8601 from API
                                    dt = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
                                    if (datetime.now(timezone.utc) - dt).total_seconds() <= cutoff_seconds:
                                        self._recent_intros[track_id] = now
                                        return True
                                except Exception:
                                    # If parsing fails, still treat as recent to be safe
                                    self._recent_intros[track_id] = now
                                    return True
                            else:
                                # No timestamp; conservatively assume recent
                                self._recent_intros[track_id] = now
                                return True
            except Exception as api_err:
                logger.warning("Recent commentary check via history failed; using in-memory only", error=str(api_err))

            return False

        except Exception as e:
            logger.error("Error checking recent commentary", error=str(e))
            return False
    
    async def _build_context(self) -> Dict[str, Any]:
        """Build context information for commentary generation"""
        try:
            # Get recent history
            history = await self.api_client.get_history(limit=5)
            recent_tracks = []

            if history and 'tracks' in history:
                for item in history['tracks']:
                    track = item.get('track', {})
                    recent_tracks.append(f"{track.get('artist')} - {track.get('title')}")

            # Get next up (if available)
            next_up = await self.api_client.get_next_up()
            upcoming = []

            if next_up and 'next_tracks' in next_up:
                for item in next_up['next_tracks'][:3]:
                    track = item.get('track', {})
                    upcoming.append(f"{track.get('artist')} - {track.get('title')}")

            # Determine if this is Christmas mode based on station name
            is_christmas = settings.STATION_NAME.lower() == 'christmas'

            return {
                'recent_history': recent_tracks,
                'up_next': upcoming,
                'station_name': settings.STATION_NAME,
                'christmas_mode': is_christmas,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error("Error building context", error=str(e))
            return {}
    
    async def _process_job(self, job: CommentaryJob):
        """Process a single commentary job"""
        async with self.job_semaphore:
            job_id = id(job)
            self.current_jobs[job_id] = job
            
            try:
                logger.info("Processing commentary job", 
                           track_title=job.track_info.get('title'),
                           track_artist=job.track_info.get('artist'))
                
                job.status = JobStatus.GENERATING_TEXT
                job.started_at = datetime.now(timezone.utc)
                gen_started = datetime.now(timezone.utc)

                # Get DJ settings from API for this station
                dj_settings = await self.api_client.get_settings(station=settings.STATION_NAME)
                # Determine current voice provider & voice for placeholder record
                try:
                    vp = (dj_settings.get('dj_voice_provider') if isinstance(dj_settings, dict) else None) or settings.DJ_VOICE_PROVIDER
                except Exception:
                    vp = 'kokoro'
                voice_id = None
                try:
                    if isinstance(dj_settings, dict):
                        if vp == 'chatterbox':
                            voice_id = dj_settings.get('chatterbox_voice') or dj_settings.get('dj_voice_id')
                        else:
                            # Default to kokoro or generic id
                            voice_id = dj_settings.get('kokoro_voice') or dj_settings.get('dj_kokoro_voice') or dj_settings.get('dj_voice_id')
                except Exception:
                    voice_id = None

                # Create a placeholder commentary record with status=running so UI can show it
                placeholder_id = None
                try:
                    provider_pref = None
                    try:
                        provider_pref = dj_settings.get('dj_provider') if isinstance(dj_settings, dict) else None
                    except Exception:
                        provider_pref = None
                    provider_pref = provider_pref or settings.DJ_PROVIDER
                    # Avoid duplicate placeholders for the same upcoming track within this process
                    track_id = None
                    try:
                        track_id = job.track_info.get('id')
                    except Exception:
                        track_id = None

                    if track_id and track_id in self._placeholders:
                        placeholder_id = self._placeholders.get(track_id)
                        logger.info("Reusing existing placeholder for track", track_id=track_id, placeholder_id=placeholder_id)
                    else:
                        placeholder = await self.api_client.create_commentary({
                            'text': '<speak>Generating…</speak>',
                            'transcript': None,
                            'provider': provider_pref,
                            'voice_provider': vp,
                            'voice_id': voice_id,
                            'status': 'running',
                            'context_data': job.context,
                        })
                        if placeholder and isinstance(placeholder, dict):
                            placeholder_id = placeholder.get('commentary_id')
                            if track_id and placeholder_id:
                                self._placeholders[track_id] = int(placeholder_id)
                                if not hasattr(self, '_placeholder_times'):
                                    self._placeholder_times = {}
                                import time as _t
                                self._placeholder_times[track_id] = _t.time()
                except Exception:
                    placeholder_id = None

                # If a kokoro voice is configured in admin settings, apply it
                try:
                    if dj_settings and dj_settings.get('dj_kokoro_voice'):
                        self.tts_service.kokoro_client.voice = dj_settings.get('dj_kokoro_voice')
                    if dj_settings and dj_settings.get('dj_tts_volume'):
                        vol = float(dj_settings.get('dj_tts_volume'))
                        # Clamp reasonable range 0.5x - 2.0x
                        vol = max(0.5, min(2.0, vol))
                        self.tts_service.kokoro_client.volume = vol
                except Exception:
                    pass
                
                # Check for cached commentary before hitting the LLM
                ssml_text = None
                transcript_full = None
                provider_used = None
                audio_file = None
                generation_time_ms = 0
                tts_time_ms = 0

                cached = None
                if track_id:
                    try:
                        cached = await self.api_client.get_cached_commentary(track_id)
                    except Exception as cache_err:
                        logger.warning("Cache lookup failed; proceeding with LLM", error=str(cache_err))

                if cached:
                    logger.info("Using cached commentary for track", track_id=track_id)
                    ssml_text = cached.get('ssml') or cached.get('text')
                    transcript_full = cached.get('transcript')
                    provider_used = 'cached'

                    # Try to reuse existing audio file
                    cached_audio = (cached.get('audio_url') or '').lstrip('/')
                    if cached_audio:
                        cached_filename = os.path.basename(cached_audio)
                        cached_path = os.path.join(settings.TTS_CACHE_DIR, cached_filename)
                        if os.path.exists(cached_path):
                            audio_file = cached_filename
                            logger.info("Reusing cached audio file", audio_file=audio_file)

                    if not audio_file and ssml_text:
                        # Audio was cleaned up — regenerate from cached SSML
                        logger.info("Cached audio missing; regenerating TTS from cached SSML", track_id=track_id)
                        tts_started = datetime.now(timezone.utc)
                        audio_file = await self.tts_service.generate_audio(
                            text=ssml_text,
                            job_id=str(job_id),
                            dj_settings=dj_settings
                        )
                        tts_time_ms = int((datetime.now(timezone.utc) - tts_started).total_seconds() * 1000)

                else:
                    # Generate commentary text, streaming tokens to WebSocket clients as they arrive
                    async def _ws_token_callback(token: str) -> None:
                        await self.api_client.broadcast_ws("commentary_token", {"token": token})

                    commentary_payload = await self.commentary_generator.generate(
                        track_info=job.track_info,
                        context=job.context,
                        dj_settings=dj_settings,
                        token_callback=_ws_token_callback,
                    )
                    gen_finished = datetime.now(timezone.utc)
                    generation_time_ms = int((gen_finished - gen_started).total_seconds() * 1000)

                    if not commentary_payload:
                        job.status = JobStatus.FAILED
                        job.error = "Failed to generate commentary text"
                        return

                    # Supports returning either a plain SSML string, or a dict with keys {ssml, transcript_full, gen_mode, provider_used}
                    if isinstance(commentary_payload, dict):
                        ssml_text = commentary_payload.get('ssml') or commentary_payload.get('text')
                        transcript_full = commentary_payload.get('transcript_full') or None
                        # Attach LLM generation metadata to context for observability
                        try:
                            gen_mode = commentary_payload.get('gen_mode')
                            if gen_mode:
                                job.context = dict(job.context or {})
                                job.context['ollama_mode'] = gen_mode
                        except Exception:
                            pass
                        # Capture the actual provider used after any fallback
                        try:
                            provider_used = commentary_payload.get('provider_used')
                        except Exception:
                            provider_used = None
                    else:
                        ssml_text = str(commentary_payload)
                        transcript_full = None
                        provider_used = None

                    # Generate audio
                    tts_started = datetime.now(timezone.utc)
                    audio_file = await self.tts_service.generate_audio(
                        text=ssml_text,
                        job_id=str(job_id),
                        dj_settings=dj_settings
                    )
                    tts_time_ms = int((datetime.now(timezone.utc) - tts_started).total_seconds() * 1000)

                if not audio_file:
                    job.status = JobStatus.FAILED
                    job.error = "Failed to generate audio"
                    return
                # Validate generated file looks like audio before proceeding
                try:
                    import os
                    file_path = os.path.join(settings.TTS_CACHE_DIR, audio_file if audio_file.endswith('.mp3') or audio_file.endswith('.wav') else audio_file)
                    is_audio = False
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            head = f.read(4)
                        size = os.path.getsize(file_path)
                        if size > 1000 and (head.startswith(b'ID3') or (len(head) >= 2 and head[0] == 0xFF and head[1] in (0xFB, 0xF3, 0xF2)) or audio_file.endswith('.wav')):
                            is_audio = True
                    if not is_audio:
                        job.status = JobStatus.FAILED
                        job.error = "Generated file is not valid audio"
                        logger.error("Generated TTS file failed validation", file=audio_file)
                        return
                except Exception:
                    pass

                job.audio_file = audio_file
                job.status = JobStatus.READY
                job.completed_at = datetime.now(timezone.utc)
                
                # Determine provider used for DB (prefer actual provider from payload; fallback to admin/env setting)
                try:
                    if not provider_used and isinstance(dj_settings, dict):
                        provider_used = dj_settings.get('dj_provider') or settings.DJ_PROVIDER
                    provider_used = provider_used or settings.DJ_PROVIDER
                except Exception:
                    provider_used = settings.DJ_PROVIDER

                # Save to database via API
                await self._save_commentary(
                    job,
                    transcript_full=transcript_full,
                    generation_time_ms=generation_time_ms,
                    tts_time_ms=tts_time_ms,
                    dj_settings=dj_settings,
                    provider_used=provider_used,
                    existing_commentary_id=placeholder_id,
                    voice_provider_used=self.tts_service.last_voice_provider,
                    voice_id_override=self.tts_service.last_voice_id
                )
                
                # Broadcast commentary_ready so the frontend can show the final transcript
                try:
                    await self.api_client.broadcast_ws("commentary_ready", {
                        "transcript": transcript_full or "",
                        "audio_url": job.audio_file,
                        "track": job.track_info.get("title"),
                        "artist": job.track_info.get("artist"),
                    })
                except Exception as bcast_err:
                    logger.debug("commentary_ready broadcast failed (non-critical)", error=str(bcast_err))

                # Inject into stream
                await self._inject_commentary(job)

                # Record that we've generated an intro for this upcoming track id to avoid duplicates
                try:
                    track_id = job.track_info.get('id')
                    if track_id:
                        self._recent_intros[int(track_id)] = time.time()
                        # Clear any placeholder tracking for this track
                        try:
                            self._placeholders.pop(int(track_id), None)
                        except Exception:
                            pass
                except Exception:
                    pass
                
                logger.info("Commentary job completed successfully",
                           duration_ms=(job.completed_at - job.started_at).total_seconds() * 1000)
            
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                logger.error("Commentary job failed",
                           error=str(e),
                           track_title=job.track_info.get('title'))

            finally:
                self.current_jobs.pop(job_id, None)
                # Clear placeholder on any non-success exit so the worker can retry
                if job.status != JobStatus.READY:
                    try:
                        _tid = job.track_info.get('id')
                        if _tid:
                            self._placeholders.pop(int(_tid), None)
                            if hasattr(self, '_placeholder_times'):
                                self._placeholder_times.pop(int(_tid), None)
                            # Add a short cooldown so the worker doesn't spin on the
                            # same track every poll interval when generation fails
                            self._recent_intros[int(_tid)] = time.time()
                    except Exception:
                        pass
    
    async def _save_commentary(
        self,
        job: CommentaryJob,
        transcript_full: Optional[str] = None,
        generation_time_ms: Optional[int] = None,
        tts_time_ms: Optional[int] = None,
        dj_settings: Optional[Dict[str, Any]] = None,
        provider_used: Optional[str] = None,
        existing_commentary_id: Optional[int] = None,
        voice_provider_used: Optional[str] = None,
        voice_id_override: Optional[str] = None,
    ):
        """Save commentary to database via API"""
        try:
            # Determine voice provider and voice_id based on actual usage
            try:
                default_voice_provider = (
                    dj_settings.get('dj_voice_provider') if isinstance(dj_settings, dict) else None
                ) or settings.DJ_VOICE_PROVIDER
            except Exception:
                default_voice_provider = 'kokoro'

            vp = voice_provider_used or default_voice_provider

            voice_id = voice_id_override
            if voice_id is None and dj_settings and isinstance(dj_settings, dict):
                if vp == 'chatterbox':
                    voice_id = dj_settings.get('chatterbox_voice') or dj_settings.get('dj_voice_id')
                elif vp == 'kokoro':
                    voice_id = (
                        dj_settings.get('kokoro_voice')
                        or dj_settings.get('dj_kokoro_voice')
                        or dj_settings.get('dj_voice_id')
                    )
                else:
                    voice_id = dj_settings.get('dj_voice_id')

            if voice_id is None:
                if vp == 'chatterbox':
                    voice_id = getattr(settings, 'CHATTERBOX_VOICE', None)
                elif vp == 'kokoro':
                    voice_id = getattr(settings, 'KOKORO_VOICE', None)

            if isinstance(voice_id, str):
                trimmed_voice = voice_id.strip()
                if len(trimmed_voice) > 100:
                    logger.warning(
                        "Voice identifier exceeds column size; truncating",
                        original_length=len(trimmed_voice),
                        provider=vp,
                    )
                    trimmed_voice = trimmed_voice[:100]
                voice_id = trimmed_voice or None

            # Use the admin-selected provider when recording, falling back to env default
            provider_used = None
            try:
                if isinstance(dj_settings, dict) and dj_settings.get('dj_provider'):
                    provider_used = dj_settings.get('dj_provider')
            except Exception:
                provider_used = None
            provider_used = provider_used or settings.DJ_PROVIDER

            commentary_data = {
                'text': job.commentary_text,
                'transcript': transcript_full,
                'audio_url': job.audio_file,
                'provider': provider_used,
                'voice_provider': vp,
                'voice_id': voice_id,
                'status': 'ready',
                'context_data': job.context,
                'duration_ms': job.audio_duration_ms,
                'generation_time_ms': generation_time_ms,
                'tts_time_ms': tts_time_ms,
                'is_intro': True,  # Mark this as an intro for the upcoming track
                'target_track_id': job.track_info.get('id')  # Track this commentary is about
            }
            
            # If we created a placeholder, update it; otherwise create fresh
            if existing_commentary_id:
                await self.api_client.update_commentary(existing_commentary_id, commentary_data)
            else:
                await self.api_client.create_commentary(commentary_data)
            
        except Exception as e:
            logger.error("Failed to save commentary", error=str(e))
    
    async def _inject_commentary(self, job: CommentaryJob):
        """Inject commentary into the audio stream"""
        try:
            if not job.audio_file:
                return

            # Before injecting, verify the target track is still "next up".
            # If it's already playing (or gone), injecting would pair this
            # commentary with the WRONG song.
            target_id = job.track_info.get('id')
            if target_id:
                try:
                    now_playing = await self.api_client.get_now_playing()
                    current_id = (now_playing or {}).get('track', {}).get('id')
                    if current_id and int(current_id) == int(target_id):
                        logger.warning(
                            "Commentary target is already playing — discarding to avoid wrong pairing",
                            track=job.track_info.get('title'),
                            track_id=target_id,
                        )
                        return
                    next_up = await self.api_client.get_next_up()
                    next_ids = [
                        t.get('track', {}).get('id')
                        for t in (next_up or {}).get('next_tracks', [])
                        if t.get('track', {}).get('id')
                    ]
                    if next_ids and int(target_id) not in [int(n) for n in next_ids]:
                        logger.warning(
                            "Commentary target no longer queued — discarding stale intro",
                            track=job.track_info.get('title'),
                            track_id=target_id,
                            actual_next=next_ids[:1],
                        )
                        return
                except Exception as check_err:
                    logger.warning("Could not verify next track before inject; proceeding anyway", error=str(check_err))

            # Tell Liquidsoap to inject the commentary for this station
            await self.api_client.inject_commentary(job.audio_file, station=settings.STATION_NAME)

            logger.info("Commentary injected into stream",
                       audio_file=job.audio_file,
                       station=settings.STATION_NAME)

        except Exception as e:
            logger.error("Failed to inject commentary", error=str(e), station=settings.STATION_NAME)
