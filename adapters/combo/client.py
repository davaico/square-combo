"""
Combo API client adapter.
"""

import logging
from typing import List, Dict, Any
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
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    async def get_locations(self) -> List[Dict[str, Any]]:
        """
        Fetch all locations from Combo API.

        Returns:
            List of location dictionaries containing:
            - id: String, the partner id
            - name: String, the location's name
            - account_id: String, the account's partner id
            - partner_id: String, the partner id
            - snapshift_account_id: Integer, the account's id
            - snapshift_location_id: Integer, the location's id
            - teams: Array[team], list of teams (empty if single team)

        Raises:
            httpx.HTTPStatusError: If API returns error status code
            httpx.ConnectError: If network connection fails
        """
        logger.info("Fetching locations from Combo API")

        try:
            response = await self.client.get("/api/v1/locations")
            response.raise_for_status()

            locations = response.json()
            logger.info(f"Successfully fetched {len(locations)} locations")

            return locations

        except Exception as e:
            logger.error(f"Failed to fetch locations: {str(e)}")
            raise

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
