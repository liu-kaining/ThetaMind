"""Database session management with async SQLAlchemy."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Create async engine with connection pool configuration (CTO Approved)
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL queries in development
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session instance
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            # Re-raise to allow FastAPI to handle the error
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database.
    
    In production, Alembic is the sole schema manager (entrypoint.sh runs
    `alembic upgrade head`).  create_all is kept only for development/testing
    convenience and is skipped when ENVIRONMENT=production.
    """
    import logging
    logger = logging.getLogger(__name__)
    from app.core.config import settings
    if settings.environment == "production":
        logger.info("Production environment — skipping create_all (Alembic is the schema authority)")
        return
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            if "already exists" not in str(e).lower():
                logger.warning(f"Database initialization warning: {e}")


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

