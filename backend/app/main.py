"""Main FastAPI application entry point."""

# Disable tqdm progress bars (FinanceToolkit) before any imports so server logs stay clean and login is not blocked
import os
os.environ.setdefault("TQDM_DISABLE", "1")

import asyncio
import logging
from contextlib import asynccontextmanager

import pytz

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.endpoints.ai import router as ai_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.company_data import router as company_data_router
from app.api.endpoints.config import router as config_router
from app.api.endpoints.market import router as market_router
from app.api.endpoints.payment import router as payment_router
from app.api.endpoints.strategy import router as strategy_router
from app.api.endpoints.tasks import router as tasks_router
from app.api.endpoints.openapi_data import router as openapi_router
from app.api.schemas import HealthResponse, RootResponse
from app.core.config import settings
from app.db.session import AsyncSessionLocal, close_db, init_db
from app.services.ai_service import ai_service
from app.services.cache import cache_service
from app.services.config_service import config_service
from app.services.scheduler import shutdown_scheduler, setup_scheduler, start_scheduler
from app.services.tiger_service import tiger_service

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Initialize database connections
    - Connect to Redis
    - Check Tiger API connectivity (Ping)
    - Start scheduler (quota reset only)
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
    if settings.debug:
        logger.info("Development CORS: Using explicit localhost origins (debug mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Requested-With",
        "Accept",
        "Accept-Language",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
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
api_v1.include_router(company_data_router)
api_v1.include_router(tasks_router)
api_v1.include_router(openapi_router)

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

