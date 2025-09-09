"""
Square API client adapter.
"""

import logging
from datetime import datetime, date, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx

from utils.config import settings

logger = logging.getLogger(__name__)


class SquareClient:
    """Client for interacting with Square API."""

    def __init__(self, access_token: str, environment: str = None):
        self.access_token = access_token
        self.environment = environment or settings.SQUARE_ENVIRONMENT
        self.base_url = self._get_base_url()
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Square-Version": "2025-08-20",  # TODO: move to settings
                "Content-Type": "application/json",
            },
        )

    def _get_base_url(self) -> str:
        """Get base URL based on environment."""
        if self.environment == "production":
            return "https://connect.squareup.com"
        else:
            return "https://connect.squareupsandbox.com"

    async def search_orders_by_date(
        self,
        location_ids: List[str],
        target_date: date,
        filter_field: str = "CLOSED_AT",
    ) -> List[Dict[str, Any]]:
        """
        Search for orders on a specific date using Square Orders API.

        Args:
            location_ids: List of Square location IDs
            target_date: Date to search for orders
            filter_field: Field to filter by ("CLOSED_AT" or "UPDATED_AT")

        Returns:
            List of order dictionaries from Square API

        Raises:
            httpx.HTTPStatusError: If API returns error status code
        """
        logger.info(f"Searching orders for {target_date} at locations {location_ids}")

        # Convert target_date to French timezone (GMT+2) date range
        # TODO: move to settings
        french_tz = timezone(timedelta(hours=2))

        # Start of day in French timezone, converted to UTC
        start_of_day_french = datetime.combine(
            target_date, datetime.min.time()
        ).replace(tzinfo=french_tz)
        start_utc = start_of_day_french.astimezone(timezone.utc)

        # End of day in French timezone, converted to UTC
        end_of_day_french = datetime.combine(target_date, datetime.max.time()).replace(
            tzinfo=french_tz
        )
        end_utc = end_of_day_french.astimezone(timezone.utc)

        # Prepare request body
        request_body = {
            "location_ids": location_ids,
            "query": {
                "filter": {
                    "date_time_filter": {
                        "field": filter_field,
                        "start_at": start_utc.isoformat().replace("+00:00", "Z"),
                        "end_at": end_utc.isoformat().replace("+00:00", "Z"),
                    }
                }
            },
            "limit": 500,  # Maximum allowed by Square API
        }

        all_orders = []
        cursor = None

        try:
            while True:
                if cursor:
                    request_body["cursor"] = cursor

                response = await self.client.post(
                    "/v2/orders/search", json=request_body
                )
                response.raise_for_status()

                data = response.json()
                orders = data.get("orders", [])
                all_orders.extend(orders)

                cursor = data.get("cursor")
                if not cursor:
                    break

                logger.info(f"Retrieved {len(orders)} orders, continuing with cursor")

            logger.info(
                f"Successfully retrieved {len(all_orders)} orders for {target_date}"
            )
            return all_orders

        except Exception as e:
            logger.error(f"Failed to search orders: {str(e)}")
            raise

    def calculate_gross_revenue(self, orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate gross revenue from a list of Square orders.

        Args:
            orders: List of Square order dictionaries

        Returns:
            Dictionary containing revenue breakdown:
            - gross_sales_amount: Total gross sales in cents
            - total_discounts: Total discounts in cents
            - total_refunds: Total refunds in cents
            - net_sales_amount: Net sales after discounts and refunds in cents
            - order_count: Number of orders processed
            - refund_count: Number of refunds processed
            - currency: Currency code (e.g., "EUR")
        """
        logger.info(f"Calculating revenue for {len(orders)} orders")

        if not orders:
            return {
                "gross_sales_amount": 0,
                "total_discounts": 0,
                "total_refunds": 0,
                "net_sales_amount": 0,
                "order_count": 0,
                "refund_count": 0,
                "currency": "EUR",  # Default currency
            }

        gross_sales = 0
        total_discounts = 0
        total_refunds = 0
        refund_count = 0
        currency = "EUR"  # Default, will be overridden by first order

        for order in orders:
            # Get currency from first order
            if order.get("total_money", {}).get("currency"):
                currency = order["total_money"]["currency"]

            # Add gross sales (total order amount)
            order_total = order.get("total_money", {}).get("amount", 0)
            gross_sales += order_total

            # Add discounts
            order_discounts = order.get("total_discount_money", {}).get("amount", 0)
            total_discounts += order_discounts

            # Process refunds/returns
            returns = order.get("returns", [])
            for return_item in returns:
                refund_count += 1
                return_amount = (
                    return_item.get("return_amounts", {})
                    .get("total_money", {})
                    .get("amount", 0)
                )
                # Return amounts are negative in Square API, make them positive for our calculation
                total_refunds += abs(return_amount)

        net_sales = gross_sales - total_discounts - total_refunds

        result = {
            "gross_sales_amount": gross_sales,
            "total_discounts": total_discounts,
            "total_refunds": total_refunds,
            "net_sales_amount": net_sales,
            "order_count": len(orders),
            "refund_count": refund_count,
            "currency": currency,
        }

        logger.info(f"Revenue calculation complete: {result}")
        return result

    async def get_daily_revenue(
        self, location_id: str, target_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch daily revenue for a specific location and date.

        Combines new sales (CLOSED_AT) and refund data (UPDATED_AT) to calculate
        net daily revenue according to Square's methodology.

        Args:
            location_id: Square location ID
            target_date: Date to fetch revenue for

        Returns:
            Revenue data dictionary with structure:
            - location_id: str
            - date: str (YYYY-MM-DD format)
            - gross_sales_amount: int (cents)
            - total_discounts: int (cents)
            - total_refunds: int (cents)
            - net_sales_amount: int (cents)
            - order_count: int
            - refund_count: int
            - currency: str
        """
        logger.info(f"Fetching revenue for location {location_id} on {target_date}")

        try:
            # Step 1: Fetch new sales (orders closed on this date)
            logger.info("Fetching new sales (CLOSED_AT)")
            new_sales_orders = await self.search_orders_by_date(
                location_ids=[location_id],
                target_date=target_date,
                filter_field="CLOSED_AT",
            )

            # Step 2: Fetch refunds (orders updated on this date due to returns)
            logger.info("Fetching refunds (UPDATED_AT)")
            refund_orders = await self.search_orders_by_date(
                location_ids=[location_id],
                target_date=target_date,
                filter_field="UPDATED_AT",
            )

            # Step 3: Calculate revenue from new sales
            new_sales_revenue = self.calculate_gross_revenue(new_sales_orders)

            # Step 4: Calculate refunds from updated orders
            refund_revenue = self.calculate_gross_revenue(refund_orders)

            # Step 5: Combine the results
            total_gross_sales = new_sales_revenue["gross_sales_amount"]
            total_discounts = new_sales_revenue["total_discounts"]
            total_refunds = (
                new_sales_revenue["total_refunds"] + refund_revenue["total_refunds"]
            )

            net_sales = total_gross_sales - total_discounts - total_refunds

            result = {
                "location_id": location_id,
                "date": target_date.strftime("%Y-%m-%d"),
                "gross_sales_amount": total_gross_sales,
                "total_discounts": total_discounts,
                "total_refunds": total_refunds,
                "net_sales_amount": net_sales,
                "order_count": new_sales_revenue["order_count"],
                "refund_count": new_sales_revenue["refund_count"]
                + refund_revenue["refund_count"],
                "currency": new_sales_revenue.get("currency", "EUR"),
            }

            logger.info(
                f"Daily revenue calculation complete: net_sales={net_sales} {result['currency']}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to calculate daily revenue: {str(e)}")
            raise

    async def get_locations(self) -> List[Dict[str, Any]]:
        logger.info("Fetching locations from Square API")
        try:
            response = await self.client.get("/v2/locations")
            response.raise_for_status()
            data = response.json()
            return data.get("locations", [])
        except Exception as e:
            logger.error(f"Failed to fetch locations from Square: {str(e)}")
            raise

    async def get_merchant_by_id(self, merchant_id: str) -> Dict[str, Any]:
        logger.info("Fetching merchant info from Square API")
        try:
            response = await self.client.get(f"/v2/merchants/{merchant_id}")
            response.raise_for_status()
            data = response.json()
            return data.get("merchant", {})
        except Exception as e:
            logger.error(f"Failed to fetch locations from Square: {str(e)}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
