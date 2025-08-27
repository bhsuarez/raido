import asyncio
import os
import signal
import sys
from typing import Dict, Any
import structlog

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.worker.dj_worker import DJWorker
from app.services.commentary_generator import CommentaryGenerator
from app.services.tts_service import TTSService

# Configure logging
configure_logging()
logger = structlog.get_logger()

class DJWorkerApp:
    """Main DJ Worker application"""
    
    def __init__(self):
        self.worker: DJWorker = None
        self.commentary_generator: CommentaryGenerator = None
        self.tts_service: TTSService = None
        self.running = False
        self.tasks = []
    
    async def setup(self):
        """Initialize services"""
        logger.info("🏴‍☠️ Setting up DJ Worker services...")
        
        # Initialize commentary generator
        self.commentary_generator = CommentaryGenerator()
        
        # Initialize TTS service
        self.tts_service = TTSService()
        
        # Initialize worker
        self.worker = DJWorker(
            commentary_generator=self.commentary_generator,
            tts_service=self.tts_service
        )
        
        logger.info("DJ Worker services initialized")
    
    async def start(self):
        """Start the worker"""
        if not self.worker:
            await self.setup()
        
        logger.info("🎙️ Starting DJ Worker...")
        self.running = True
        
        # Start the main worker task
        worker_task = asyncio.create_task(self.worker.run())
        self.tasks.append(worker_task)
        
        # Start health check server
        health_task = asyncio.create_task(self._start_health_server())
        self.tasks.append(health_task)
        
        logger.info("DJ Worker started successfully")
        
        # Wait for tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Worker tasks cancelled")
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info("🛑 Stopping DJ Worker...")
        self.running = False
        
        if self.worker:
            await self.worker.stop()
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("DJ Worker stopped")
    
    async def _start_health_server(self):
        """Start a simple health check server"""
        from aiohttp import web, web_runner
        
        async def health_handler(request):
            status = {
                "status": "healthy" if self.running else "stopping",
                "worker_active": self.worker.is_running if self.worker else False,
                "service": "raido-dj-worker"
            }
            return web.json_response(status)
        
        app = web.Application()
        app.router.add_get('/health', health_handler)
        
        runner = web_runner.AppRunner(app)
        await runner.setup()
        
        site = web_runner.TCPSite(runner, '0.0.0.0', 8001)
        await site.start()
        
        logger.info("Health server started on port 8001")
        
        # Keep the server running
        while self.running:
            await asyncio.sleep(1)
        
        await runner.cleanup()

async def main():
    """Main entry point"""
    app = DJWorkerApp()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(app.stop())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error in main", error=str(e))
        sys.exit(1)
    finally:
        await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(0)