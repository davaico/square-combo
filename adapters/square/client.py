"""Square completed-order totals minus dated, completed payment refunds."""

import logging
from datetime import date, datetime

import httpx

from utils.config import settings
from utils.dates import business_interval
from utils.http import request_json

logger = logging.getLogger(__name__)


class SquareClient:
    def __init__(self, access_token: str):
        self.client = httpx.AsyncClient(
            base_url=settings.square_base_url,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Square-Version": settings.SQUARE_API_VERSION,
            },
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def close(self):
        await self.client.aclose()

    async def _pages(
        self, method: str, path: str, key: str, *, body=None, params=None
    ) -> list[dict]:
        records = []
        seen = set()
        for _ in range(settings.MAX_API_PAGES):
            data = await request_json(self.client, method, path, json=body, params=params)
            records.extend(data.get(key, []))
            cursor = data.get("cursor")
            if not cursor:
                return records
            if cursor in seen:
                raise ValueError("Provider repeated a pagination cursor")
            seen.add(cursor)
            if body is not None:
                body = {**body, "cursor": cursor}
            else:
                params = {**(params or {}), "cursor": cursor}
        raise ValueError("Provider exceeded pagination limit")

    async def search_orders_by_date(self, location_ids: list[str], target_date: date) -> list[dict]:
        start, end = business_interval(target_date)
        orders = await self._pages(
            "POST",
            "/v2/orders/search",
            "orders",
            body={
                "location_ids": location_ids,
                "query": {
                    "filter": {
                        "date_time_filter": {
                            "closed_at": {"start_at": start.isoformat(), "end_at": end.isoformat()}
                        },
                        "state_filter": {"states": ["COMPLETED"]},
                    }
                },
                "limit": 500,
            },
        )
        # Apply a half-open interval locally too: adjacent days must never overlap.
        result = self._unique_in_interval(orders, "closed_at", start, end)
        logger.info("Retrieved %d completed orders", len(result))
        return result

    @staticmethod
    def _unique_in_interval(
        records: list[dict], timestamp: str, start: datetime, end: datetime
    ) -> list[dict]:
        result = {}
        for record in records:
            moment = datetime.fromisoformat(record[timestamp].replace("Z", "+00:00"))
            if moment.tzinfo is None:
                raise ValueError("Provider timestamp has no timezone")
            if start <= moment < end:
                if record["id"] in result and record != result[record["id"]]:
                    raise ValueError("Provider returned conflicting duplicate records")
                result[record["id"]] = record
        return list(result.values())

    async def get_refunds_by_date(self, location_id: str, target_date: date) -> list[dict]:
        start, end = business_interval(target_date)
        refunds = await self._pages(
            "GET",
            "/v2/refunds",
            "refunds",
            params={
                "location_id": location_id,
                "begin_time": start.isoformat(),
                "end_time": end.isoformat(),
                "status": "COMPLETED",
                "limit": 100,
            },
        )
        return self._unique_in_interval(refunds, "created_at", start, end)

    @staticmethod
    def _money(money: dict) -> int:
        if money["currency"] != settings.REVENUE_CURRENCY:
            raise ValueError("Provider currency differs from configured revenue currency")
        amount = money["amount"]
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("Provider amount must be nonnegative integer minor units")
        return amount

    async def get_daily_revenue(self, location_id: str, target_date: date) -> dict:
        orders = await self.search_orders_by_date([location_id], target_date)
        refunds = await self.get_refunds_by_date(location_id, target_date)
        sales = sum(
            self._money(order["total_money"])
            for order in orders
            if order["state"] == "COMPLETED" and order["location_id"] == location_id
        )
        returned = sum(
            self._money(refund["amount_money"])
            for refund in refunds
            if refund["status"] == "COMPLETED" and refund["location_id"] == location_id
        )
        return {
            "location_id": location_id,
            "date": target_date.isoformat(),
            "sales_amount": sales,
            "total_refunds": returned,
            "net_sales_amount": sales - returned,
            "order_count": len(orders),
            "refund_count": len(refunds),
            "currency": settings.REVENUE_CURRENCY,
        }

    async def get_locations(self) -> list[dict]:
        data = await request_json(self.client, "GET", "/v2/locations")
        return [
            location for location in data.get("locations", []) if location.get("status") == "ACTIVE"
        ]

    async def get_merchant_by_id(self, merchant_id: str) -> dict:
        data = await request_json(self.client, "GET", f"/v2/merchants/{merchant_id}")
        return data["merchant"]
