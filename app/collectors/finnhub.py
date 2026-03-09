"""
Finnhub News Collector

Collects stock news from Finnhub News API with async HTTP client.
Reference: https://finnhub.io/docs/api/stock-news
"""
import httpx
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FinnhubArticle(BaseModel):
    """Finnhub news article model."""
    datetime: int
    headline: str
    id: str
    image: str
    related: List[str]
    source: str
    summary: str
    url: str
    category: str


class FinnhubCollector:
    """Finnhub news collector with async HTTP client."""

    BASE_URL = "https://finnhub.io/api/v1/stock/news"

    def __init__(self, api_key: str, timeout: float = 10.0):
        """
        Initialize Finnhub collector.

        Args:
            api_key: Finnhub API key (required)
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout

    async def get_company_news(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles for a company.

        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of normalized article dictionaries
        """
        params = {
            "token": self.api_key,
            "symbol": symbol,
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()

                raw_articles = response.json()
                return [self.normalize_article(article) for article in raw_articles]

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching news for {symbol}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def normalize_article(self, raw_article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Finnhub article to standard format.

        Args:
            raw_article: Raw article from Finnhub

        Returns:
            Normalized article dictionary with keys:
                - title: Article headline
                - url: Article URL
                - source: "finnhub"
                - content: Article summary
                - published_at: datetime object
                - provider_article_id: Original Finnhub ID
        """
        try:
            return {
                "title": raw_article.get("headline", ""),
                "url": raw_article.get("url", ""),
                "source": "finnhub",
                "content": raw_article.get("summary", ""),
                "published_at": datetime.fromtimestamp(raw_article.get("datetime", 0))
                if raw_article.get("datetime")
                else None,
                "provider_article_id": raw_article.get("id", ""),
            }
        except Exception as e:
            logger.warning(f"Error normalizing article: {e}")
            return {}
