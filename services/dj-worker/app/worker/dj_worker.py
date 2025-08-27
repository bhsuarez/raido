import asyncio
import time
from typing import Optional, Dict, Any
import structlog
from datetime import datetime, timezone

from app.core.config import settings
from app.services.commentary_generator import CommentaryGenerator
from app.services.tts_service import TTSService
from app.services.api_client import APIClient
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
        """Main worker loop"""
        self.is_running = True
        logger.info("🎙️ DJ Worker started")
        
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
            # Check if we need to generate commentary based on recent plays
            should_generate = await self._should_generate_commentary()
            
            if should_generate:
                # Get current track info
                current_track = await self.api_client.get_now_playing()
                
                if current_track and current_track.get('track'):
                    job = CommentaryJob(
                        track_info=current_track['track'],
                        play_info=current_track.get('play'),
                        context=await self._build_context()
                    )
                    
                    # Process the job
                    await self._process_job(job)
        
        except Exception as e:
            logger.error("Error processing pending jobs", error=str(e))
    
    async def _should_generate_commentary(self) -> bool:
        """Determine if commentary should be generated"""
        try:
            # Check settings for commentary interval
            settings_response = await self.api_client.get_settings()
            if not settings_response:
                return False
            
            interval = int(settings_response.get('dj_commentary_interval', 1))
            enabled = settings_response.get('enable_commentary', True)
            
            if not enabled:
                return False
            
            # Get recent play history to check if commentary is due
            history = await self.api_client.get_history(limit=interval)
            if not history or 'tracks' not in history:
                return False
            
            recent_tracks = history['tracks']
            
            # Check if any recent tracks need commentary
            for track_play in recent_tracks[:interval]:
                if not track_play.get('commentary'):
                    # This track doesn't have commentary yet
                    return True
            
            return False
        
        except Exception as e:
            logger.error("Error checking if commentary should be generated", error=str(e))
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
                'duration_ms': job.audio_duration_ms
            }
            
            # Associate with current play if available
            if job.play_info and job.play_info.get('id'):
                commentary_data['play_id'] = job.play_info['id']
            
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