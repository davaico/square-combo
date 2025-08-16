"""
Combo API client adapter.
"""

import logging
from datetime import date
from typing import List, Dict, Any, Optional
import httpx

from utils.config import settings

logger = logging.getLogger(__name__)


class ComboClient:
    """Client for interacting with Combo API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = settings.COMBO_BASE_URL
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",  # Adjust auth method as needed
                "Content-Type": "application/json",
            }
        )

    async def get_locations(self) -> List[Dict[str, Any]]:
        """
        Fetch all locations from Combo API.

        Returns:
            List of location dictionaries
        """
        # TODO: Implement Combo locations API call
        logger.info("Fetching locations from Combo API")
        pass

    async def post_revenue(
        self, location_id: str, revenue_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post daily revenue data to Combo API.

        Args:
            location_id: Combo location ID
            revenue_data: Revenue data to post

        Returns:
            API response dictionary
        """
        # TODO: Implement Combo revenue posting API call
        logger.info(f"Posting revenue data to Combo for location {location_id}")
        pass

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
