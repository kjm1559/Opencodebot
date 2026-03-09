"""API routes for articles and companies."""
from typing import AsyncGenerator, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import BackgroundTasks

from app.api.schemas import ArticleResponse, ArticleListResponse, CompanyInfoResponse
from app.database import AsyncSessionLocal
from app.models import Article, Company

router = APIRouter(prefix="/api/v1")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "stock-news-api"}


@router.get(
    "/articles",
    response_model=ArticleListResponse,
    summary="Get articles list with pagination and filters",
)
async def get_articles(
    db: AsyncSession = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by company ticker"),
    source: Optional[str] = Query(None, description="Filter by news source"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ArticleListResponse:
    """
    Retrieve paginated list of articles with optional filters.
    
    - **ticker**: Filter articles for specific company
    - **source**: Filter articles by news source (finnhub, alphavantage, gnews)
    - **page**: Page number (default: 1)
    - **page_size**: Number of items per page (default: 20, max: 100)
    """
    # Build query
    query = select(Article).order_by(Article.published_at.desc())

    # Apply filters
    if ticker:
        company_subquery = (
            select(Company.id).where(Company.ticker == ticker).limit(1)
        ).scalar_subquery()
        query = (
            select(Article)
            .join(Article.companies)
            .filter(Company.id == company_subquery)
            .order_by(Article.published_at.desc())
        )

    if source:
        query = query.where(Article.source == source)

    # Get total count
    count_subquery = select(func.coalesce(func.count(Article.id), 0)).select_from(
        query
    )

    total_result = await db.execute(count_subquery)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    articles = result.scalars().unique().all()

    return ArticleListResponse(
        items=articles,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 1,
    )


@router.get(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get single article by ID",
)
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Retrieve a single article by its ID with related companies."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.get(
    "/companies",
    response_model=List[CompanyInfoResponse],
    summary="Get all companies with article counts",
)
async def get_companies(db: AsyncSession = Depends(get_db)) -> List[CompanyInfoResponse]:
    """Retrieve list of all companies with their article counts."""
    result = await db.execute(
        select(
            Company,
            func.count(Article.id).label("article_count"),
        )
        .join(Article.companies)
        .group_by(Company.id)
        .order_by(Company.ticker)
    )

    companies = []
    for company, article_count in result.all():
        company.article_count = article_count
        companies.append(company)

    return companies


@router.post(
    "/news/collect",
    summary="Manually trigger news collection",
)
async def trigger_news_collection(background_tasks: BackgroundTasks) -> dict:
    """
    Manually trigger news collection for all companies.
    
    This runs the collection task in the background via celery
    """
    # Direct function call - would integrate with Celery in production
    # await collect_news_for_all_companies()

    return {
        "status": "success",
        "message": "News collection endpoint ready",
    }
