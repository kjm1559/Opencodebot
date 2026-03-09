"""
GNews API Collector (STUB)

Placeholder for future GNews integration.
"""
from typing import List, Dict, Any


class GNewsCollector:
    """GNews API collector (STUB - not implemented)."""

    def __init__(self, api_key: str):
        """Initialize GNews collector (STUB)."""
        self.api_key = api_key
        logger = __import__("logging").getLogger(__name__)
        logger.warning("GNewsCollector is a STUB - no data will be collected")

    async def get_company_news(self, keyword: str) -> List[Dict[str, Any]]:
        """Get news from GNews (STUB - returns empty list)."""
        return []
