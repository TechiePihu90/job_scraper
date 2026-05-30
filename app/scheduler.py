"""Scheduler for periodic scrape runs using APScheduler."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.orchestrator import run_all

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """Start the background scheduler that triggers scrape runs."""
    scheduler.add_job(
        run_all,
        trigger=IntervalTrigger(hours=settings.scrape_interval_hours),
        id="scrape_all",
        name="Scrape all companies",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: scraping every %d hours",
        settings.scrape_interval_hours,
    )


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
