"""Pytest fixtures and configuration."""
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine

from app.config import get_settings
from app.database import async_engine, AsyncSessionLocal
from app.models import Base
from app.main import app


@pytest.fixture()
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def test_database():
    """Create test database tables."""
    test_url = "postgresql+asyncpg://stocknews:stocknews@localhost:5432/stocknews_test"
    engine = create_async_engine(test_url, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture()
async def test_db_session(test_database):
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_database,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture()
async def client():
    """Create AsyncClient for API tests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
