"""Square OAuth uses the same environment as revenue reads."""

from urllib.parse import urlencode

import httpx

from utils.config import settings
from utils.http import request_json


class SetupService:
    def get_square_authentication_url(self, state: str) -> str:
        if not settings.SQUARE_CLIENT_ID or not settings.SQUARE_CLIENT_SECRET:
            raise ValueError("Square OAuth credentials are not configured")
        query = urlencode(
            {
                "client_id": settings.SQUARE_CLIENT_ID,
                "scope": "PAYMENTS_READ ORDERS_READ MERCHANT_PROFILE_READ",
                "state": state,
                "redirect_uri": f"{settings.APP_URL}/square-auth/callback",
            }
        )
        return f"{settings.square_base_url}/oauth2/authorize?{query}"

    async def _token(self, grant: dict) -> dict:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            # Authorization codes are one-use, and refresh tokens can rotate: no automatic replay.
            return await request_json(
                client,
                "POST",
                f"{settings.square_base_url}/oauth2/token",
                retry_safe=False,
                json={
                    "client_id": settings.SQUARE_CLIENT_ID,
                    "client_secret": settings.SQUARE_CLIENT_SECRET,
                    **grant,
                },
            )

    async def obtain_square_access_token(self, code: str) -> dict:
        return await self._token(
            {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.APP_URL}/square-auth/callback",
            }
        )

    async def refresh_square_access_token(self, refresh_token: str) -> dict:
        return await self._token({"refresh_token": refresh_token, "grant_type": "refresh_token"})
