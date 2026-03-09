"""Unit tests for SQLAlchemy models."""
import pytest
from datetime import datetime
from app.models import Company, Article, ArticleCompany, ArticleSignal


class TestCompanyModel:
    """Test Company model."""

    def test_create_company(self):
        """Test company creation."""
        company = Company(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Technology",
            is_active=True,
        )
        assert company.ticker == "AAPL"
        assert company.name == "Apple Inc."
        assert company.is_active is True
        assert company.sector == "Technology"


class TestArticleModel:
    """Test Article model."""

    def test_create_article(self):
        """Test article creation."""
        article = Article(
            title="Test Article",
            url="https://example.com/test",
            source="finnhub",
            content="Test content",
        )
        assert article.title == "Test Article"
        assert article.content_hash == Article.compute_hash(
            "Test Article", "https://example.com/test"
        )

    def test_compute_hash(self):
        """Test hash computation."""
        hash1 = Article.compute_hash("Test Title", "https://example.com/test")
        hash2 = Article.compute_hash("Test Title", "https://example.com/test")
        hash3 = Article.compute_hash("Different Title", "https://example.com/test")
        
        assert len(hash1) == 64
        assert hash1 == hash2
        assert hash1 != hash3

    def test_different_articles_same_hash_different_urls(self):
        """Test that same title with different URLs produces different hashes."""
        hash1 = Article.compute_hash("Same Title", "https://example.com/url1")
        hash2 = Article.compute_hash("Same Title", "https://example.com/url2")
        
        assert hash1 != hash2


class TestArticleCompanyModel:
    """Test ArticleCompany association."""

    def test_create_article_company(self):
        """Test article-company association."""
        article_company = ArticleCompany(
            article_id=1,
            company_id=1,
        )
        assert article_company.article_id == 1
        assert article_company.company_id == 1


class TestArticleSignalModel:
    """Test ArticleSignal model."""

    def test_create_signal(self):
        """Test signal creation."""
        signal = ArticleSignal(
            article_id=1,
            sentiment_score=0.8,
            relevance_score=0.9,
        )
        assert signal.article_id == 1
        assert signal.sentiment_score == 0.8
        assert signal.relevance_score == 0.9