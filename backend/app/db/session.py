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
    """Initialize database (create tables)."""
    # Use create_all with checkfirst=True to avoid errors if tables already exist
    async with engine.begin() as conn:
        # SQLAlchemy's create_all doesn't have checkfirst in async mode,
        # so we catch the exception if tables already exist
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            # If tables already exist, that's fine - just log and continue
            import logging
            logger = logging.getLogger(__name__)
            if "already exists" not in str(e).lower():
                # Only log if it's not a "table already exists" error
                logger.warning(f"Database initialization warning: {e}")
            # Continue anyway - tables might already exist


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()

