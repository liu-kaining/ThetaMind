"""APScheduler configuration for scheduled tasks."""

import logging
from datetime import datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, update

from app.db.models import Anomaly, DailyPick, Task, User
from app.db.session import AsyncSessionLocal
from app.core.config import settings
from app.api.endpoints.tasks import create_task_async
from app.services.anomaly_service import AnomalyService
from sqlalchemy import delete
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

# Initialize Scheduler
scheduler = AsyncIOScheduler()

# Define Timezones
UTC = pytz.UTC
EST = pytz.timezone("US/Eastern")


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


async def generate_daily_picks_job() -> None:
    """
    Generate daily picks via Task System.
    Runs at 08:30 AM EST (Market Open Pre-game).
    Creates a system task (user_id=None) to run the pipeline.
    """
    today = datetime.now(EST).date()
    lock_key = f"lock:scheduler:daily_picks:{today}"
    
    # Try to acquire lock for 1 hour
    # This prevents multiple workers from creating the same task
    if not await cache_service.acquire_lock(lock_key, ttl=3600):
        logger.debug(f"ℹ️ Lock for {lock_key} already acquired by another worker. Skipping.")
        return

    async with AsyncSessionLocal() as session:
        try:
            # Check idempotency: Don't regenerate if already exists for this market date
            result = await session.execute(
                select(DailyPick).where(DailyPick.date == today)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"ℹ️ Daily picks already exist for {today} (EST). Skipping.")
                return

            logger.info(f"🚀 Creating Daily Picks generation task for {today} (EST)...")
            
            # Create system task (user_id=None)
            task = await create_task_async(
                db=session,
                user_id=None,  # System task
                task_type="daily_picks",
                metadata={"date": str(today)},
            )
            await session.commit()

            logger.info(f"✅ Daily picks task {task.id} created for {today} (EST).")
        except Exception as e:
            logger.error(f"❌ Failed to create daily picks task: {e}", exc_info=True)
            await session.rollback()


async def scan_anomalies() -> None:
    """
    每 5 分钟扫描异动
    检测期权异动并存储到数据库
    """
    lock_key = "lock:scheduler:anomaly_scan"
    
    # Try to acquire lock for 280 seconds (slightly less than 5 minutes)
    if not await cache_service.acquire_lock(lock_key, ttl=280):
        logger.debug(f"ℹ️ Lock for {lock_key} already acquired by another worker. Skipping scan.")
        return

    async with AsyncSessionLocal() as session:
        try:
            logger.info("🚀 Creating Anomaly Scan task...")
            
            # Create system task (user_id=None)
            task = await create_task_async(
                db=session,
                user_id=None,
                task_type="anomaly_scan",
                metadata={"trigger": "scheduler"},
            )
            await session.commit()

            logger.info(f"✅ Anomaly scan task {task.id} created.")
        except Exception as e:
            logger.error(f"❌ Failed to create anomaly scan task: {e}", exc_info=True)
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

    # Job 2: Daily Picks (08:30 EST) - only when feature enabled
    if settings.enable_daily_picks:
        scheduler.add_job(
            generate_daily_picks_job,
            trigger=CronTrigger(hour=8, minute=30, timezone=EST),
            id="generate_daily_picks",
            replace_existing=True,
        )

    # Job 3: Anomaly Radar (每 5 分钟扫描异动) - only when feature enabled
    if settings.enable_anomaly_radar:
        scheduler.add_job(
            scan_anomalies,
            trigger='interval',
            minutes=5,
            id="scan_anomalies",
            replace_existing=True,
        )

    jobs_desc = ["Quota Reset"]
    if settings.enable_daily_picks:
        jobs_desc.append("Daily Picks")
    if settings.enable_anomaly_radar:
        jobs_desc.append("Anomaly Radar")
    logger.info("Scheduler configured with jobs: %s.", ", ".join(jobs_desc))


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