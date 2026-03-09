from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Text,
    Index,
    func,
)
from sqlalchemy.sql import func
import hashlib
from datetime import datetime

Base = declarative_base()


class Company(Base):
    """Company model for stock ticker information."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    articles = relationship(
        "Article",
        secondary="article_companies",
        back_populates="companies",
        lazy="dynamic",
    )


class Article(Base):
    """Article model for news content with deduplication."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(2000), unique=True, nullable=False)
    source = Column(String(50), nullable=False)
    provider_article_id = Column(String(200))
    published_at = Column(DateTime(timezone=True))
    content = Column(Text)
    content_hash = Column(String(64), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_articles_source", "source"),
        Index("ix_articles_published_at", "published_at"),
        UniqueConstraint("content_hash"),
    )

    # Relationships
    companies = relationship(
        "Company",
        secondary="article_companies",
        back_populates="articles",
        lazy="dynamic",
    )
    signal = relationship("ArticleSignal", uselist=False, back_populates="article", cascade="all, delete-orphan")

    @staticmethod
    def compute_hash(title: str, url: str) -> str:
        """Compute SHA-256 hash of title and url concatenated.

        Args:
            title: Article title
            url: Article URL

        Returns:
            64-character hex digest string
        """
        return hashlib.sha256(f"{title}{url}".encode()).hexdigest()


class ArticleCompany(Base):
    """Association table for many-to-many relationship between Article and Company."""

    __tablename__ = "article_companies"

    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (UniqueConstraint("article_id", "company_id"),)


class ArticleSignal(Base):
    """Article Signal model for sentiment and relevance scores."""

    __tablename__ = "article_signals"

    id = Column(Integer, primary_key=True)
    article_id = Column(
        Integer,
        ForeignKey("articles.id", ondelete="CASCADE"),
        unique=True,
    )
    sentiment_score = Column(Float)
    relevance_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    article = relationship("Article", back_populates="signal")
