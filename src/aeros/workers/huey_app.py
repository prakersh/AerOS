"""Huey task queue application — lightweight background worker for AEROS."""

import asyncio
import importlib
import signal
import time
from typing import Any

import structlog

logger = structlog.get_logger()

REMINDER_INTERVAL = 300
TELEMETRY_INTERVAL = 3600

_running = True


def _shutdown(signum: int, frame: Any) -> None:
    global _running
    logger.info("worker.shutdown_signal", signal=signum)
    _running = False


def main() -> None:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    reminders_mod = importlib.import_module("aeros.workers.reminders")
    telemetry_mod = importlib.import_module("aeros.workers.telemetry_retention")

    logger.info("worker.started", pid=__import__("os").getpid())

    last_reminder = 0.0
    last_telemetry = 0.0
    loop = asyncio.new_event_loop()

    while _running:
        now = time.time()

        if now - last_reminder >= REMINDER_INTERVAL:
            try:
                loop.run_until_complete(reminders_mod.check_and_send_reminders())
                last_reminder = now
            except Exception as e:
                logger.error("worker.reminder_error", error=str(e))

        if now - last_telemetry >= TELEMETRY_INTERVAL:
            try:
                telemetry_mod.cleanup_old_telemetry()
                last_telemetry = now
            except Exception as e:
                logger.error("worker.telemetry_error", error=str(e))

        time.sleep(10)

    loop.close()
    logger.info("worker.stopped")


if __name__ == "__main__":
    main()
