import logging
import secrets
import httpx
from typing import List, Optional
from urllib.request import Request

from sqlalchemy.orm import Session
from database.models import Client, Location
from utils.config import settings

from pydantic_models import SquareObtainTokenResponse

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

    async def obtain_square_access_token(self, auth_code: str) -> SquareObtainTokenResponse:
        request = {
            "client_id": settings.SQUARE_CLIENT_ID,
            "client_secret": settings.SQUARE_CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code"
        }
        response = await self.client.post(f"{settings.SQUARE_BASE_URL}/oauth2/token", json=request)
        data = response.json()
        return SquareObtainTokenResponse.model_validate(data)
