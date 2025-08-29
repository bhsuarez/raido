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
            # Check if DJ provider is disabled
            if settings.DJ_PROVIDER == "disabled":
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
                
            # Check settings for commentary
            settings_response = await self.api_client.get_settings()
            if not settings_response:
                return False
            
            interval = int(settings_response.get('dj_commentary_interval', 1))
            enabled = settings_response.get('enable_commentary', True)
            
            if not enabled:
                return False
            
            # Get current playing track info to determine timing
            now_playing = await self.api_client.get_now_playing()
            if not now_playing or 'current' not in now_playing:
                return False
            
            current_play = now_playing['current']
            if not current_play:
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
            # This would ideally check the database for recent commentary for this track
            # For now, we'll use a simple approach and let the API handle duplicates
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
                
                # Get DJ settings from API
                dj_settings = await self.api_client.get_settings()
                
                # Generate commentary text
                commentary_text = await self.commentary_generator.generate(
                    track_info=job.track_info,
                    context=job.context,
                    dj_settings=dj_settings
                )
                
                if not commentary_text:
                    job.status = JobStatus.FAILED
                    job.error = "Failed to generate commentary text"
                    return
                
                job.commentary_text = commentary_text
                job.status = JobStatus.GENERATING_AUDIO
                
                # Generate audio
                audio_file = await self.tts_service.generate_audio(
                    text=commentary_text,
                    job_id=str(job_id)
                )
                
                if not audio_file:
                    job.status = JobStatus.FAILED
                    job.error = "Failed to generate audio"
                    return
                
                job.audio_file = audio_file
                job.status = JobStatus.READY
                job.completed_at = datetime.now(timezone.utc)
                
                # Save to database via API
                await self._save_commentary(job)
                
                # Inject into stream
                await self._inject_commentary(job)
                
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
    
    async def _save_commentary(self, job: CommentaryJob):
        """Save commentary to database via API"""
        try:
            commentary_data = {
                'text': job.commentary_text,
                'audio_url': job.audio_file,
                'provider': settings.DJ_PROVIDER,
                'voice_provider': settings.DJ_VOICE_PROVIDER,
                'status': 'ready',
                'context_data': job.context,
                'duration_ms': job.audio_duration_ms,
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