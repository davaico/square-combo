"""
Square API client adapter.
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import httpx

from utils.config import settings

logger = logging.getLogger(__name__)


class SquareClient:
    """Client for interacting with Square API."""
    
    def __init__(self, access_token: str, application_id: str):
        self.access_token = access_token
        self.application_id = application_id
        self.base_url = self._get_base_url()
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Square-Version": "2023-10-18",  # Use latest stable version
                "Content-Type": "application/json"
            }
        )
    
    def _get_base_url(self) -> str:
        """Get base URL based on environment."""
        if settings.SQUARE_ENVIRONMENT == "production":
            return "https://connect.squareup.com"
        else:
            return "https://connect.squareupsandbox.com"
    
    async def get_locations(self) -> List[Dict[str, Any]]:
        """
        Fetch all locations for the authenticated merchant.
        
        Returns:
            List of location dictionaries
        """
        # TODO: Implement Square locations API call
        logger.info("Fetching locations from Square API")
        pass
    
    async def get_daily_revenue(
        self, 
        location_id: str, 
        target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch daily revenue for a specific location and date.
        
        Args:
            location_id: Square location ID
            target_date: Date to fetch revenue for
            
        Returns:
            Revenue data dictionary or None if no data
        """
        # TODO: Implement Square orders/payments API call
        logger.info(f"Fetching revenue for location {location_id} on {target_date}")
        pass
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
