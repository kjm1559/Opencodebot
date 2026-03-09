"""Seed initial company data into database."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_engine
from app.models import Company, Article, Base
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

# Seed data
SEED_COMPANIES = [
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "is_active": True},
    {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "is_active": True},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Communication Services", "is_active": True},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Cyclical", "is_active": True},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Cyclical", "is_active": True},
]

async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def seed_companies():
    """Seed companies into database."""
    async with async_session_maker() as session:
        for company_data in SEED_COMPANIES:
            # Check if company already exists
            result = await session.execute(
                select(Company).where(Company.ticker == company_data["ticker"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"⚠️  Company {company_data['ticker']} already exists, skipping")
                continue

            # Create new company
            company = Company(**company_data)
            session.add(company)
            print(f"✅ Added company: {company_data['ticker']} - {company_data['name']}")

        await session.commit()
        print(f"\n✅ Seeding complete: {len(SEED_COMPANIES)} companies processed")


if __name__ == "__main__":
    print("🌱 Starting company data seeding...\n")
    asyncio.run(seed_companies())
