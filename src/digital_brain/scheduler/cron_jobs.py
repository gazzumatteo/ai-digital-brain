"""Standalone scheduler for distributed memory reinforcement.

Run as: python -m digital_brain.scheduler.cron_jobs

Extends the existing reflection scheduler with:
- Hourly working memory reinforcement
- Daily semantic consolidation (full reinforcement + pruning)
"""

from __future__ import annotations

import asyncio
import logging
import signal

from apscheduler.schedulers.background import BackgroundScheduler

from digital_brain.config import get_settings
from digital_brain.memory.manager import MemoryManager
from digital_brain.memory.reinforcer import MemoryReinforcer

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_shutdown_event = asyncio.Event()


def _run_reinforcement(user_id: str) -> None:
    """Synchronous wrapper for a reinforcement cycle."""
    settings = get_settings()
    manager = MemoryManager(settings=settings)
    reinforcer = MemoryReinforcer(manager, settings.distributed)
    stats = reinforcer.reinforcement_cycle(user_id)
    logger.info("Hourly reinforcement for %s: %s", user_id, stats)


def _run_consolidation(user_id: str) -> None:
    """Full consolidation: reinforcement + pruning."""
    settings = get_settings()
    manager = MemoryManager(settings=settings)
    reinforcer = MemoryReinforcer(manager, settings.distributed)
    stats = reinforcer.reinforcement_cycle(user_id)
    logger.info("Daily consolidation for %s: %s", user_id, stats)


def _handle_signal(signum: int, _frame: object) -> None:
    """Graceful shutdown handler."""
    logger.info("Received signal %d, shutting down...", signum)
    _shutdown_event.set()


def start_scheduler(user_ids: list[str] | None = None) -> BackgroundScheduler:
    """Configure and start the distributed memory scheduler."""
    global _scheduler
    settings = get_settings()
    ds = settings.distributed

    if user_ids is None:
        user_ids = ["default"]

    _scheduler = BackgroundScheduler()

    for uid in user_ids:
        # Hourly reinforcement
        _scheduler.add_job(
            _run_reinforcement,
            trigger="interval",
            hours=ds.reinforcement_interval_hours,
            args=[uid],
            id=f"reinforcement_{uid}",
            replace_existing=True,
        )

        # Daily consolidation
        _scheduler.add_job(
            _run_consolidation,
            trigger="cron",
            hour=ds.consolidation_hour,
            args=[uid],
            id=f"consolidation_{uid}",
            replace_existing=True,
        )

        logger.info(
            "Scheduled reinforcement (every %dh) and consolidation (at %02d:00) for user %s",
            ds.reinforcement_interval_hours,
            ds.consolidation_hour,
            uid,
        )

    _scheduler.start()
    return _scheduler


def main() -> None:
    """Entry point for standalone scheduler."""
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info("Starting distributed memory scheduler...")
    scheduler = start_scheduler()

    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_shutdown_event.wait())
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
