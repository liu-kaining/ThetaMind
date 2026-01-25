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
            stmt = update(User).values(daily_ai_usage=0, daily_image_usage=0)
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
    async with AsyncSessionLocal() as session:
        try:
            service = AnomalyService()
            anomalies = await service.detect_anomalies()

            if not anomalies:
                logger.debug("No anomalies detected in this scan")
                return

            # 清理 1 小时前的旧数据
            from datetime import timezone as tz
            cutoff = datetime.now(tz.utc) - timedelta(hours=1)
            await session.execute(
                delete(Anomaly).where(Anomaly.detected_at < cutoff)
            )

            # 插入新数据
            for anomaly in anomalies:
                anomaly_record = Anomaly(
                    symbol=anomaly['symbol'],
                    anomaly_type=anomaly['type'],
                    score=int(anomaly.get('score', 0)),
                    details=anomaly.get('details', {}),
                    ai_insight=anomaly.get('ai_insight'),
                    detected_at=datetime.now(tz.utc)
                )
                session.add(anomaly_record)

            await session.commit()
            logger.info(f"✅ Anomalies detected: {len(anomalies)}")

        except Exception as e:
            logger.error(f"❌ Failed to scan anomalies: {e}", exc_info=True)
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

    # Job 3: Anomaly Radar (每 5 分钟扫描异动)
    scheduler.add_job(
        scan_anomalies,
        trigger='interval',
        minutes=5,
        id="scan_anomalies",
        replace_existing=True,
    )

    logger.info("Scheduler configured with 3 jobs (Quota Reset, Daily Picks & Anomaly Radar).")


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