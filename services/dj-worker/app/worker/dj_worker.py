import asyncio
import time
from typing import Optional, Dict, Any
import structlog
from datetime import datetime, timezone

from app.core.config import settings
from app.services.commentary_generator import CommentaryGenerator
from app.services.tts_service import TTSService
from app.services.api_client import APIClient
# Temporarily disabled due to psutil import issues
# from app.services.system_monitor import system_monitor
system_monitor = None
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
    
    async def run(self):
        """Main worker loop with system health monitoring"""
        self.is_running = True
        logger.info("🎙️ DJ Worker started")
        
        # Schedule periodic system health monitoring
        health_monitor_task = asyncio.create_task(self._periodic_health_monitoring())
        
        try:
            while self.is_running:
                await self._process_pending_jobs()
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
                    if system_monitor.is_protection_active():
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
    
    async def _process_pending_jobs(self):
        """Check for and process pending commentary jobs"""
        try:
            # Check if we need to generate commentary based on current track timing
            should_generate = await self._should_generate_commentary()
            
            if should_generate:
                # Get the next upcoming track to generate commentary for
                next_track = await self._get_next_track_for_commentary()
                
                if next_track and next_track.get('track'):
                    job = CommentaryJob(
                        track_info=next_track['track'],
                        play_info=None,  # No play record yet for upcoming track
                        context=await self._build_context()
                    )
                    
                    # Process the job
                    await self._process_job(job)
        
        except Exception as e:
            logger.error("Error processing pending jobs", error=str(e))
    
    async def _should_generate_commentary(self) -> bool:
        """Determine if commentary should be generated for next track"""
        try:
            # Load settings first to respect admin selections over env defaults
            settings_response = await self.api_client.get_settings()
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
            # Get upcoming tracks
            next_up = await self.api_client.get_next_up()
            if not next_up or 'next_tracks' not in next_up:
                return None
            
            # Get the first upcoming track that doesn't have commentary prepared
            for next_track in next_up['next_tracks'][:1]:  # Just check the very next track
                track = next_track.get('track')
                if track:
                    # Check if this track already has recent commentary prepared
                    # (to avoid generating multiple commentaries for the same track)
                    track_id = track.get('id')
                    if track_id and not await self._has_recent_commentary(track_id):
                        return next_track
            
            return None
        
        except Exception as e:
            logger.error("Error getting next track for commentary", error=str(e))
            return None
    
    async def _has_recent_commentary(self, track_id: int) -> bool:
        """Check if a track has recent commentary (within last hour)"""
        try:
            import time as _time
            now = _time.time()
            # Prune very old entries
            cutoff = now - 3600  # 1 hour TTL
            self._recent_intros = {tid: ts for tid, ts in self._recent_intros.items() if ts >= cutoff}

            last = self._recent_intros.get(track_id)
            return bool(last and last >= cutoff)
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
            
            return {
                'recent_history': recent_tracks,
                'up_next': upcoming,
                'station_name': settings.STATION_NAME,
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
                
                # Get DJ settings from API
                dj_settings = await self.api_client.get_settings()

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
                
                # Generate commentary text
                commentary_payload = await self.commentary_generator.generate(
                    track_info=job.track_info,
                    context=job.context,
                    dj_settings=dj_settings
                )
                gen_finished = datetime.now(timezone.utc)
                generation_time_ms = int((gen_finished - gen_started).total_seconds() * 1000)
                
                if not commentary_payload:
                    job.status = JobStatus.FAILED
                    job.error = "Failed to generate commentary text"
                    return

                # Supports returning either a plain SSML string, or a dict with keys {ssml, transcript_full}
                if isinstance(commentary_payload, dict):
                    ssml_text = commentary_payload.get('ssml') or commentary_payload.get('text')
                    transcript_full = commentary_payload.get('transcript_full') or None
                else:
                    ssml_text = str(commentary_payload)
                    transcript_full = None

                job.commentary_text = ssml_text
                job.status = JobStatus.GENERATING_AUDIO
                tts_started = datetime.now(timezone.utc)
                
                # Generate audio
                audio_file = await self.tts_service.generate_audio(
                    text=ssml_text,
                    job_id=str(job_id),
                    dj_settings=dj_settings
                )
                tts_finished = datetime.now(timezone.utc)
                tts_time_ms = int((tts_finished - tts_started).total_seconds() * 1000)
                
                if not audio_file:
                    job.status = JobStatus.FAILED
                    job.error = "Failed to generate audio"
                    return
                
                job.audio_file = audio_file
                job.status = JobStatus.READY
                job.completed_at = datetime.now(timezone.utc)
                
                # Save to database via API
                await self._save_commentary(
                    job,
                    transcript_full=transcript_full,
                    generation_time_ms=generation_time_ms,
                    tts_time_ms=tts_time_ms,
                    dj_settings=dj_settings
                )
                
                # Inject into stream
                await self._inject_commentary(job)

                # Record that we've generated an intro for this upcoming track id to avoid duplicates
                try:
                    track_id = job.track_info.get('id')
                    if track_id:
                        self._recent_intros[int(track_id)] = time.time()
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
    
    async def _save_commentary(
        self,
        job: CommentaryJob,
        transcript_full: Optional[str] = None,
        generation_time_ms: Optional[int] = None,
        tts_time_ms: Optional[int] = None,
        dj_settings: Optional[Dict[str, Any]] = None,
    ):
        """Save commentary to database via API"""
        try:
            # Determine voice_id based on provider selection
            try:
                # Prefer dynamic admin setting when available
                vp = (dj_settings.get('dj_voice_provider') if isinstance(dj_settings, dict) else None) or settings.DJ_VOICE_PROVIDER
            except Exception:
                vp = 'kokoro'
            if dj_settings and isinstance(dj_settings, dict):
                if vp == 'xtts':
                    voice_id = dj_settings.get('xtts_voice') or dj_settings.get('dj_voice_id')
                else:
                    voice_id = dj_settings.get('kokoro_voice') or dj_settings.get('dj_voice_id')
            else:
                voice_id = None

            commentary_data = {
                'text': job.commentary_text,
                'transcript': transcript_full,
                'audio_url': job.audio_file,
                'provider': settings.DJ_PROVIDER,
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
            
            # For upcoming tracks, don't associate with a play_id yet
            # The commentary will be matched when the track actually plays
            
            await self.api_client.create_commentary(commentary_data)
            
        except Exception as e:
            logger.error("Failed to save commentary", error=str(e))
    
    async def _inject_commentary(self, job: CommentaryJob):
        """Inject commentary into the audio stream"""
        try:
            if not job.audio_file:
                return
            
            # Tell Liquidsoap to inject the commentary
            await self.api_client.inject_commentary(job.audio_file)
            
            logger.info("Commentary injected into stream", audio_file=job.audio_file)
            
        except Exception as e:
            logger.error("Failed to inject commentary", error=str(e))
