"""Pydantic response schemas for API endpoints."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ArticleSignalResponse(BaseModel):
    """Article sentiment and relevance scores."""
    sentiment_score: Optional[float] = Field(None, ge=-1, le=1, description="Sentiment score from -1 to 1")
    relevance_score: Optional[float] = Field(None, ge=0, le=1, description="Relevance score from 0 to 1")

    class Config:
        from_attributes = True


class ArticleCompanyResponse(BaseModel):
    """Company information linked to article."""
    id: int
    ticker: str
    name: str
    sector: Optional[str] = None

    class Config:
        from_attributes = True


class ArticleResponse(BaseModel):
    """Article response schema."""
    id: int
    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    content: Optional[str] = None
    content_hash: str
    created_at: datetime
    companies: List[ArticleCompanyResponse] = Field(default=[], description="Companies mentioned in article")
    signal: Optional[ArticleSignalResponse] = Field(None, description="AI-generated sentiment/relevance scores")

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """List of articles with pagination."""
    items: List[ArticleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanyInfoResponse(BaseModel):
    """Company information."""
    id: int
    ticker: str
    name: str
    sector: Optional[str] = None
    is_active: bool
    article_count: int = 0

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class TaskStatusResponse(BaseModel):
    """Celery task status response."""
    task_id: str
    status: str
    result: Optional[dict] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
