"""Async database configuration with connection pooling."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from contextlib import asynccontextmanager

from app.config import get_settings
from app.models import Base

settings = get_settings()

# Async engine with connection pooling
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Critical for connection health
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def get_db():
    """Dependency injection function for async DB sessions.
    
    Yields:
        AsyncSession: Database session
    """
    async def _get_db():
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    return _get_db()


async def init_db():
    """Create all tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db():
    """Dispose database engine."""
    await async_engine.dispose()
