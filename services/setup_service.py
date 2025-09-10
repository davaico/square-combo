import logging
import secrets
import httpx
from typing import List, Optional, Any
from urllib.request import Request

from sqlalchemy.orm import Session
from database.models import Client, Location
from utils.config import settings

logger = logging.getLogger(__name__)

class SetupService:
    """Service class for Square-Combo initialization."""
    def __init__(self, db: Session):
        self.db = db
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
            },
        )

    def get_square_authentication_url(self) -> str:
        state = secrets.token_urlsafe(32)
        return (f"{settings.SQUARE_BASE_URL}/oauth2/authorize"
                f"?client_id={settings.SQUARE_CLIENT_ID}"
                f"&scope=PAYMENTS_READ+ORDERS_READ+CUSTOMERS_READ+MERCHANT_PROFILE_READ+ITEMS_READ"
                f"&state={state}")

    async def obtain_square_access_token(self, auth_code: str) -> Optional[dict[str, Any]]:
        try:
            request = {
                "client_id": settings.SQUARE_CLIENT_ID,
                "client_secret": settings.SQUARE_CLIENT_SECRET,
                "code": auth_code,
                "grant_type": "authorization_code"
            }

            response = await self.client.post(
                f"{settings.SQUARE_BASE_URL}/oauth2/token",
                json=request,
            )

            response.raise_for_status()
            return response.json()

        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Failed to obtain Square access token: {e}")
            return None

    async def refresh_square_access_token(self, refresh_token: str) -> Optional[dict[str, Any]]:
        try:
            request = {
                "client_id": settings.SQUARE_CLIENT_ID,
                "client_secret": settings.SQUARE_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }

            response = await self.client.post(
                f"{settings.SQUARE_BASE_URL}/oauth2/token",
                json=request,
            )

            response.raise_for_status()
            return response.json()

        except (httpx.HTTPError, ValueError) as e:
            logger.error(f"Failed to refresh Square access token: {e}")
            return None

