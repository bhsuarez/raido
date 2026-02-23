"""Entrypoint for the Voicing Engine worker service.

Run with:
    python -m app.voicing_main
"""

import asyncio
import signal
import sys
import structlog

from app.core.logging_config import configure_logging
from app.worker.voicing_worker import VoicingWorker

configure_logging()
logger = structlog.get_logger()


async def main():
    worker = VoicingWorker()

    loop = asyncio.get_event_loop()

    def _shutdown(signum, frame):
        logger.info("Signal received, stopping voicing worker", signal=signum)
        asyncio.create_task(worker.stop())

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Voice of Raido — Voicing Engine starting")
    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    except Exception as e:
        logger.error("Fatal error in voicing worker", error=str(e))
        sys.exit(1)
    finally:
        await worker.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
