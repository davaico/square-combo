"""Combo Partner API; revenue POST updates the value for a location/date."""

from decimal import Decimal

import httpx

from utils.config import settings
from utils.http import request_json


class ComboClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=settings.COMBO_BASE_URL,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def get_locations(self) -> list[dict]:
        result = await request_json(self.client, "GET", "/api/v1/locations")
        if not isinstance(result, list):
            raise ValueError("Invalid Combo locations response")
        return result

    async def post_revenue(self, location_id: str, date: str, amount: Decimal) -> dict:
        # JSON's numeric representation is required by Combo; arithmetic stays in minor units.
        return await request_json(
            self.client,
            "POST",
            "/api/v1/revenues",
            json={
                "location_id": location_id,
                "date": date,
                "amount": float(amount),
            },
        )
