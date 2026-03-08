"""Entrypoint for the TTS worker service.

Run with:
    python -m app.tts_main
"""

import asyncio
import signal
import sys
import structlog

from app.core.logging_config import configure_logging
from app.worker.tts_worker import TtsWorker

configure_logging()
logger = structlog.get_logger()


async def main():
    worker = TtsWorker()

    def _shutdown(signum, frame):
        logger.info("Signal received, stopping TTS worker", signal=signum)
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Voice of Raido — TTS Worker starting")
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error in TTS worker", error=str(e))
        sys.exit(1)
    finally:
        await worker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
