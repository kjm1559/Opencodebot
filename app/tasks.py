"""
Celery tasks for news collection and maintenance.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.config import get_settings
from app.database import async_engine, AsyncSessionLocal
from app.models import Company, Article
from app.collectors.finnhub import FinnhubCollector

logger = logging.getLogger(__name__)
settings = get_settings()

# Create async session maker for tasks
async_session_maker = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@shared_task(name="collect_news_for_all_companies")
async def collect_news_for_all_companies() -> dict:
    """
    Scheduled task to collect news for all active companies.
    
    Runs every 5 minutes via Celery Beat.
    
    Returns:
        Dict with collection statistics
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting news collection for all companies")
    logger.info("=" * 60)

    async with async_session_maker() as session:
        # Get all active companies
        result = await session.execute(
            select(Company).filter(Company.is_active == True)  # noqa: E712
        )
        companies = result.scalars().all()

        if not companies:
            logger.warning("No active companies found in database")
            return {"total_companies": 0, "total_articles_added": 0}

        logger.info(f"Found {len(companies)} active companies")

        # Create Finnhub collector
        collector = FinnhubCollector(settings.finnhub_api_key)

        total_added = 0
        companies_with_errors = []

        for company in companies:
            try:
                # Collect news from last 24 hours to avoid rate limits
                from_date = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d")
                to_date = datetime.utcnow().strftime("%Y-%m-%d")

                articles = await collector.get_company_news(
                    symbol=company.ticker,
                    from_date=from_date,
                    to_date=to_date,
                )

                if not articles:
                    logger.warning(f"No articles found for {company.ticker}")
                    continue

                # Add articles to database
                added_count = await _add_articles_to_db(
                    session=session,
                    articles=articles,
                    company=company,
                )

                total_added += added_count
                logger.info(
                    f"✨ {company.ticker}: {added_count} new articles (total: {len(articles)})"
                )

                # Rate limiting - wait 1 second between requests
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"❌ Error collecting news for {company.ticker}: {e}")
                companies_with_errors.append(company.ticker)
                continue

        logger.info("=" * 60)
        logger.info(f"✅ Collection complete: {total_added} new articles")
        logger.info(f"📊 Companies: {len(companies)}, Errors: {len(companies_with_errors)}")
        logger.info("=" * 60)

        return {
            "total_companies": len(companies),
            "total_articles_added": total_added,
            "companies_with_errors": companies_with_errors,
        }


async def _add_articles_to_db(
    session: AsyncSession,
    articles: list,
    company: Company,
) -> int:
    """
    Add articles to database with deduplication.
    
    Args:
        session: Async database session
        articles: List of normalized article dictionaries
        company: Company model instance
    
    Returns:
        Number of new articles added
    """
    added_count = 0

    for article_data in articles:
        # Skip empty articles
        if not article_data or not article_data.get("title") or not article_data.get("url"):
            continue

        # Compute hash for deduplication
        content_hash = Article.compute_hash(
            article_data["title"], article_data["url"]
        )

        # Check if article already exists
        result = await session.execute(
            select(Article).filter(Article.content_hash == content_hash)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.debug(
                f"🔄 Duplicate article detected: {article_data['title'][:50]}..."
            )
            continue

        # Create new article
        article = Article(
            title=article_data["title"],
            url=article_data["url"],
            source=article_data.get("source", "finnhub"),
            content=article_data.get("content", ""),
            published_at=article_data.get("published_at"),
            content_hash=content_hash,
            provider_article_id=article_data.get("provider_article_id"),
        )

        # Link article to company
        article.companies.append(company)
        session.add(article)
        added_count += 1

    return added_count


@shared_task(name="cleanup_old_articles", bind=True, max_retries=3)
async def cleanup_old_articles(self) -> dict:
    """
    Scheduled task to delete articles older than 90 days.
    
    Runs daily at 3 AM via Celery Beat.
    """
    logger.info("🧹 Starting cleanup of old articles")

    try:
        async with async_session_maker() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            # Delete old articles
            result = await session.execute(
                select(Article).filter(Article.published_at < cutoff_date)
            )
            old_articles = result.scalars().all()

            deleted_count = len(old_articles)

            if deleted_count > 0:
                # Delete in batches to avoid memory issues
                while old_articles:
                    batch = old_articles[:100]
                    for article in batch:
                        session.delete(article)
                    await session.commit()
                    old_articles = old_articles[100:]

                logger.info(f"✅ Deleted {deleted_count} articles older than 90 days")

            return {"deleted_count": deleted_count}

    except Exception as exc:
        logger.error(f"❌ Cleanup failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 10)  # Retry after 10 minutes


@shared_task(name="collect_news_on_startup")
async def collect_news_on_startup() -> dict:
    """
    One-time collection task run on application startup.
    
    Useful for populating initial data when the system starts.
    """
    logger.info("🔄 Running initial news collection on startup")
    return await collect_news_for_all_companies()
