"""
Combo API client adapter.
"""

import logging
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
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def get_locations(self) -> Optional[List[Dict[str, Any]]]:
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
        self, location_id: str, date: str, amount: float
    ) -> Dict[str, Any]:
        """
        Post daily revenue data to Combo API.

        Args:
            location_id: The partner ID of the location.
            date: The date of the revenue in ISO 8601 format (YYYY-MM-DD).
            amount: The actual revenue amount.

        Returns:
            API response dictionary.

        Raises:
            httpx.HTTPStatusError: If API returns error status code.
        """
        logger.info(f"Posting revenue for location {location_id} on {date}: {amount}")

        payload = {
            "location_id": location_id,
            "date": date,
            "amount": amount,
        }

        try:
            response = await self.client.post("/api/v1/revenues", json=payload)
            response.raise_for_status()
            logger.info(f"Successfully posted revenue for location {location_id}")
            return response.json()

        except Exception as e:
            logger.error(f"Failed to post revenue for location {location_id}: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
