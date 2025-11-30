"""APScheduler configuration for scheduled tasks."""

import logging
from datetime import datetime

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from app.db.models import DailyPick, User
from app.db.session import AsyncSessionLocal
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# Define Timezones
UTC = pytz.UTC
EST = pytz.timezone("US/Eastern")


async def reset_daily_ai_usage() -> None:
    """
    Reset daily_ai_usage to 0 for all users.
    Runs at 00:00 UTC daily.
    """
    async with AsyncSessionLocal() as session:
        try:
            stmt = update(User).values(daily_ai_usage=0)
            await session.execute(stmt)
            await session.commit()
            logger.info("✅ Daily AI usage quota reset for all users.")
        except Exception as e:
            logger.error(f"❌ Failed to reset daily AI usage: {e}", exc_info=True)
            await session.rollback()


async def generate_daily_picks_job() -> None:
    """
    Generate daily picks.
    Runs at 08:30 AM EST (Market Open Pre-game).
    """
    async with AsyncSessionLocal() as session:
        try:
            # Critical: Always use EST date for Market Data consistency
            today = datetime.now(EST).date()
            
            # Check idempotency: Don't regenerate if already exists for this market date
            result = await session.execute(
                select(DailyPick).where(DailyPick.date == today)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"ℹ️ Daily picks already exist for {today} (EST). Skipping.")
                return

            logger.info(f"🚀 Starting Daily Picks generation for {today} (EST)...")
            
            # Generate picks via AI Service
            picks = await ai_service.generate_daily_picks()
            
            # Validate picks before saving
            if not picks or len(picks) == 0:
                raise ValueError("AI service returned empty picks list - cannot save to database")

            # Save to database
            daily_pick = DailyPick(
                date=today,
                content_json=picks,
            )
            session.add(daily_pick)
            await session.commit()

            logger.info(f"✅ Daily picks generated and saved for {today} (EST).")
        except Exception as e:
            logger.error(f"❌ Failed to generate daily picks: {e}", exc_info=True)
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

    # Job 2: Daily Picks (08:30 EST)
    # Aligns with US Market Pre-open analysis
    scheduler.add_job(
        generate_daily_picks_job,
        trigger=CronTrigger(hour=8, minute=30, timezone=EST),
        id="generate_daily_picks",
        replace_existing=True,
    )

    logger.info("Scheduler configured with 2 jobs (Quota Reset & Daily Picks).")


def start_scheduler() -> None:
    """Start the scheduler if not running."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")