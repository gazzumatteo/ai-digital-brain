"""APScheduler job definitions for the Digital Brain.

The main job is the Reflection Agent ("digital sleep"), scheduled to run
during off-peak hours to consolidate memories.
"""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from digital_brain.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_reflection_sync(user_id: str) -> None:
    """Synchronous wrapper for the async reflection job."""
    from digital_brain.agents.orchestrator import DigitalBrainOrchestrator

    async def _run() -> None:
        orchestrator = DigitalBrainOrchestrator()
        summary = await orchestrator.reflect(user_id=user_id)
        logger.info("Reflection for user %s: %s", user_id, summary[:200])

    asyncio.run(_run())


def schedule_reflection(user_ids: list[str]) -> BackgroundScheduler:
    """Set up the cron-based Reflection Agent for the given user IDs.

    Args:
        user_ids: List of user IDs to run reflection for.

    Returns:
        The configured (and started) scheduler.
    """
    global _scheduler
    settings = get_settings()

    _scheduler = BackgroundScheduler()

    for uid in user_ids:
        _scheduler.add_job(
            _run_reflection_sync,
            trigger="cron",
            hour=settings.reflection.schedule_hour,
            minute=settings.reflection.schedule_minute,
            args=[uid],
            id=f"reflection_{uid}",
            replace_existing=True,
        )
        logger.info(
            "Scheduled reflection for user %s at %02d:%02d",
            uid,
            settings.reflection.schedule_hour,
            settings.reflection.schedule_minute,
        )

    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
