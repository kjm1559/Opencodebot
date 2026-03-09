"""Integration tests for API endpoints."""
import pytest
from httpx import AsyncClient
from datetime import datetime
from app.models import Company, Article


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint returns 200."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


class TestArticlesEndpoint:
    """Test articles API."""

    @pytest.mark.asyncio
    async def test_get_empty_articles_list(self, client: AsyncClient, test_db_session):
        """Test articles endpoint returns empty list when no articles."""
        response = await client.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_articles_list_with_seed_data(
        self, client: AsyncClient, test_db_session
    ):
        """Test articles endpoint after seeding data."""
        # Create test company
        company = Company(ticker=\"\"AAPL\"\", name=\"\"Apple Inc.\"\", sector=\"\"Technology\"\")
        test_db_session.add(company)
        await test_db_session.flush()

        # Create test article
        article = Article(
            title=\"\"Test Article\"\",
            url=\"\"https://example.com/test\"\",
            source=\"\"finnhub\"\",
            content=\"\"Test content\"\",
            published_at=datetime.utcnow(),
        )
        article.companies.append(company)
        test_db_session.add(article)
        await test_db_session.commit()

        # Fetch articles
        response = await client.get("/api/v1/articles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Test Article"

    @pytest.mark.asyncio
    async def test_get_articles_with_pagination(
        self, client: AsyncClient, test_db_session
    ):
        """Test pagination works correctly."""
        response = await client.get("/api/v1/articles?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data[\"\"page\"\"] == 1
        assert data["page_size"] == 10


class TestCompaniesEndpoint:
    """Test companies API."""

    @pytest.mark.asyncio
    async def test_get_empty_companies_list(self, client: AsyncClient, test_db_session):
        """Test companies endpoint returns empty list."""
        response = await client.get("/api/v1/companies")
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_get_companies_list(self, client: AsyncClient, test_db_session):
        """Test companies endpoint returns seeded companies."""
        company = Company(ticker=\"\"AAPL\"\", name=\"\"Apple Inc.\"\", sector=\"\"Technology\"\")
        test_db_session.add(company)
        await test_db_session.commit()

        response = await client.get("/api/v1/companies")
        assert response.status_code == 200
        companies = response.json()
        assert len(companies) == 1
        assert companies[0]["ticker"] == "AAPL"
