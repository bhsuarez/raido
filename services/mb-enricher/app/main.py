"""MusicBrainz enricher service entry point."""
import asyncio
import signal
import sys
import structlog
from aiohttp import web

from app.worker.enricher import MBEnricher

logger = structlog.get_logger()


async def main():
    enricher = MBEnricher()

    # Simple health server so docker healthcheck works
    async def health(_):
        return web.json_response({"status": "healthy", "service": "mb-enricher"})

    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8002)
    await site.start()

    def _stop(sig, frame):
        logger.info("Shutdown signal received", signal=sig)
        asyncio.create_task(enricher.stop())

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    try:
        await enricher.run()
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
