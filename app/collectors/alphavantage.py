"""
AlphaVantage News Collector (STUB)

Placeholder for future AlphaVantage integration.
"""
from typing import List, Dict, Any


class AlphaVantageCollector:
    """AlphaVantage news collector (STUB - not implemented)."""

    def __init__(self, api_key: str):
        """Initialize AlphaVantage collector (STUB)."""
        self.api_key = api_key
        logger = __import__("logging").getLogger(__name__)
        logger.warning("AlphaVantageCollector is a STUB - no data will be collected")

    async def get_company_news(self, symbol: str) -> List[Dict[str, Any]]:
        """Get news from AlphaVantage (STUB - returns empty list)."""
        return []
