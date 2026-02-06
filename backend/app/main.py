"""Main FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pytz

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.endpoints.ai import router as ai_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.config import router as config_router
from app.api.endpoints.market import router as market_router
from app.api.endpoints.payment import router as payment_router
from app.api.endpoints.strategy import router as strategy_router
from app.api.endpoints.tasks import router as tasks_router
from app.api.schemas import HealthResponse, RootResponse
from app.core.config import settings
from app.db.models import DailyPick
from app.db.session import AsyncSessionLocal, close_db, init_db
from app.services.ai_service import ai_service
from app.services.cache import cache_service
from app.services.scheduler import shutdown_scheduler, setup_scheduler, start_scheduler
from app.services.tiger_service import tiger_service

logger = logging.getLogger(__name__)

# Timezone constants
EST = pytz.timezone("US/Eastern")


async def check_and_generate_daily_picks() -> None:
    """Check if daily picks exist for today, generate if missing (Cold Start)."""
    async with AsyncSessionLocal() as session:
        try:
            # Use EST date for market consistency (same as scheduler)
            today = datetime.now(EST).date()
            # Check if picks exist for today
            from sqlalchemy import select

            result = await session.execute(
                select(DailyPick).where(DailyPick.date == today)
            )
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"Daily picks already exist for {today} (EST)")
                return

            # Generate picks in background with error handling
            logger.info(f"No daily picks found for {today} (EST) - generating in background")
            task = asyncio.create_task(generate_daily_picks_async())
            
            # Add error callback to handle failures
            def handle_task_error(task: asyncio.Task) -> None:
                try:
                    task.result()  # This will raise if task failed
                except Exception as e:
                    logger.error(f"Background daily picks generation failed: {e}", exc_info=True)
            
            task.add_done_callback(handle_task_error)
        except Exception as e:
            logger.error(f"Error checking daily picks: {e}", exc_info=True)
            # Don't fail startup, but log the error


async def generate_daily_picks_async() -> None:
    """Generate daily picks asynchronously."""
    async with AsyncSessionLocal() as session:
        try:
            picks = await ai_service.generate_daily_picks()
            
            # Validate picks before saving
            if not picks or len(picks) == 0:
                logger.warning("AI service returned empty picks list - skipping save")
                return
            
            # Use EST date for consistency
            today = datetime.now(EST).date()
            daily_pick = DailyPick(
                date=today,
                content_json=picks,
            )
            session.add(daily_pick)
            await session.commit()
            logger.info(f"Daily picks generated successfully for {today} (EST)")
        except (ValueError, RuntimeError) as e:
            # Configuration or model availability errors - log but don't crash
            logger.warning(f"Daily picks generation skipped: {e}")
            await session.rollback()
            # Don't re-raise - allow app to continue
        except Exception as e:
            # Other errors - log but don't crash the app
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            await session.rollback()
            # Don't re-raise - allow app to continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database connections
    - Connect to Redis
    - Check Tiger API connectivity (Ping)
    - Check and generate daily picks if missing (Cold Start)
    - Start scheduler
    """
    # Startup
    logger.info("Starting ThetaMind backend...")

    # Initialize database (critical - fail fast if this doesn't work)
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        # Re-raise - database is critical
        raise

    # Connect to Redis (non-critical - continue if it fails)
    try:
        await cache_service.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed (continuing anyway): {e}")
        # Don't fail startup if Redis is unavailable

    # Check Tiger API connectivity (non-critical - don't block startup)
    try:
        tiger_available = await tiger_service.ping()
        if tiger_available:
            logger.info("Tiger API is reachable")
        else:
            logger.warning("Tiger API is not reachable - service may be degraded")
    except Exception as e:
        logger.warning(f"Tiger API ping failed (continuing anyway): {e}")
        # Don't fail startup if Tiger API is unavailable

    # Cold Start: Check daily picks only when feature enabled (non-critical - don't block startup)
    if settings.enable_daily_picks:
        try:
            await check_and_generate_daily_picks()
        except Exception as e:
            logger.warning(f"Daily picks check failed (continuing anyway): {e}")
        # Don't fail startup if daily picks generation fails

    # Setup and start scheduler (non-critical - don't block startup)
    try:
        setup_scheduler()
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler setup failed (continuing anyway): {e}")
        # Don't fail startup if scheduler fails

    logger.info("ThetaMind backend startup completed successfully!")

    yield

    # Shutdown
    logger.info("Shutting down ThetaMind backend...")
    shutdown_scheduler()
    await cache_service.disconnect()
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI application
# Disable Swagger/ReDoc in production for security
app = FastAPI(
    title="ThetaMind API",
    description="US Stock Option Strategy Analysis Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# CORS middleware configuration
# In production, use explicit allowed origins from environment variables
if settings.is_production:
    if settings.allowed_origins:
        # Parse comma-separated string into list
        allowed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
        logger.info(f"Production CORS: Using explicit allowed origins: {allowed_origins}")
    elif settings.domain:
        # Auto-generate origins from domain
        domain = settings.domain.strip()
        # Remove protocol if present
        if domain.startswith("http://") or domain.startswith("https://"):
            base_url = domain
        else:
            base_url = f"https://{domain}"
        allowed_origins = [base_url, f"https://{domain}", f"http://{domain}"]
        logger.info(f"Production CORS: Auto-generated from domain: {allowed_origins}")
    else:
        # Production requires explicit configuration
        logger.warning("⚠️  PRODUCTION WARNING: No ALLOWED_ORIGINS or DOMAIN set! CORS will be restrictive.")
        allowed_origins = []
else:
    # Development: allow localhost and common dev ports
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:80",
        "http://localhost:5300",  # Backend port (for direct access)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:80",
        "http://127.0.0.1:5300",  # Backend port (for direct access)
        "http://localhost",
        "http://127.0.0.1",
    ]
    # In debug mode, allow all for easier testing
    if settings.debug:
        allowed_origins = ["*"]
        logger.info("Development CORS: Allowing all origins (debug mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Create API v1 router with version prefix
api_v1 = APIRouter(prefix="/api/v1")

# Include all feature routers in v1
api_v1.include_router(auth_router)
api_v1.include_router(config_router)
api_v1.include_router(market_router)
api_v1.include_router(ai_router)
api_v1.include_router(strategy_router)
api_v1.include_router(payment_router)
api_v1.include_router(admin_router)
api_v1.include_router(tasks_router)

# Include v1 router in main app
app.include_router(api_v1)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for Docker and load balancers.

    Returns:
        HealthResponse: Health status
    """
    return HealthResponse(status="healthy", environment=settings.environment)


@app.get("/", response_model=RootResponse)
async def root() -> RootResponse:
    """
    Root endpoint.

    Returns:
        RootResponse: API information
    """
    return RootResponse(
        message="ThetaMind API",
        version="0.1.0",
        docs="/docs",
    )

