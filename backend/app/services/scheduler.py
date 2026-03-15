"""APScheduler configuration for scheduled tasks."""

import logging
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import update

from app.db.models import User
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.services.cache import cache_service
from app.services.radar_service import scan_and_alert

logger = logging.getLogger(__name__)

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# Define Timezones
UTC = pytz.UTC


async def reset_daily_ai_usage() -> None:
    """
    Reset daily_ai_usage and daily_image_usage to 0 for all users.
    Runs at 00:00 UTC daily.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = update(User).values(
                daily_ai_usage=0,
                daily_image_usage=0,
                daily_fundamental_queries_used=0,
            )
            await session.execute(stmt)
            await session.commit()
            logger.info("✅ Daily AI usage and image usage quota reset for all users.")
        except Exception as e:
            logger.error(f"❌ Failed to reset daily AI usage: {e}", exc_info=True)
            await session.rollback()


def setup_scheduler() -> None:
    """Configure and start the scheduler jobs."""
    
    # Job 1: Reset Quota (00:00 UTC)
    # This ensures global users get fresh quota every 24h
    scheduler.add_job(
        reset_daily_ai_usage,
        trigger=CronTrigger(hour=0, minute=0, timezone=UTC),
        id="reset_ai_usage",
        replace_existing=True,
    )

    # Job 2: Alpha Radar — scan top gainers/losers and push Telegram alerts every 30 min
    scheduler.add_job(
        scan_and_alert,
        trigger=IntervalTrigger(minutes=30),
        id="radar_scan_and_alert",
        replace_existing=True,
    )

    logger.info("Scheduler configured: Quota Reset + Alpha Radar (30 min).")


def start_scheduler() -> None:
    """Start the scheduler if enabled and not running."""
    if not settings.enable_scheduler:
        logger.info("Scheduler is disabled (ENABLE_SCHEDULER=False). Skipping startup.")
        return
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")