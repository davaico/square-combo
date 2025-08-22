"""
Unit tests for SquareClient with mocked HTTP responses.
"""

import pytest
import httpx
import respx
from datetime import date
from typing import List, Dict, Any

from adapters.square.client import SquareClient


@pytest.mark.asyncio
class TestSquareClientSearchOrders:
    """Test cases for SquareClient.search_orders_by_date() method."""

    @respx.mock
    async def test_search_orders_by_date_success(
        self,
        square_client: SquareClient,
        mock_square_orders_response: List[Dict[str, Any]]
    ):
        """Test successful orders search for a specific date."""
        # Mock the API response
        mock_response = {
            "orders": mock_square_orders_response,
            "cursor": None
        }
        respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call the method
        target_date = date(2025, 8, 22)
        result = await square_client.search_orders_by_date(
            location_ids=["loc_456"],
            target_date=target_date
        )

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "order_123"
        assert result[1]["id"] == "order_456"

    @respx.mock
    async def test_search_orders_by_date_empty_results(
        self,
        square_client: SquareClient,
        mock_square_empty_orders: List[Dict[str, Any]]
    ):
        """Test orders search with no results."""
        # Mock empty response
        mock_response = {
            "orders": mock_square_empty_orders,
            "cursor": None
        }
        respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call the method
        target_date = date(2025, 8, 22)
        result = await square_client.search_orders_by_date(
            location_ids=["loc_456"],
            target_date=target_date
        )

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 0

    @respx.mock
    async def test_search_orders_correct_date_range(
        self,
        square_client: SquareClient
    ):
        """Test that correct date range is sent in request."""
        # Mock the API response
        mock_request = respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json={"orders": [], "cursor": None})
        )

        # Call the method
        target_date = date(2025, 8, 22)
        await square_client.search_orders_by_date(
            location_ids=["loc_456"],
            target_date=target_date
        )

        # Check request body
        assert mock_request.called
        request_body = mock_request.calls[0].request.content.decode()

        # Should contain French timezone date range (GMT+2)
        assert "2025-08-21T22:00:00Z" in request_body  # Start of day in UTC (00:00 GMT+2)
        assert "2025-08-22T21:59:59" in request_body   # End of day in UTC (23:59 GMT+2) - may have microseconds
        assert "CLOSED_AT" in request_body
        assert "loc_456" in request_body

    @respx.mock
    async def test_search_orders_with_updated_at_filter(
        self,
        square_client: SquareClient
    ):
        """Test orders search with UPDATED_AT filter for refunds."""
        # Mock the API response
        mock_request = respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json={"orders": [], "cursor": None})
        )

        # Call the method with UPDATED_AT filter
        target_date = date(2025, 8, 22)
        await square_client.search_orders_by_date(
            location_ids=["loc_456"],
            target_date=target_date,
            filter_field="UPDATED_AT"
        )

        # Check request body contains UPDATED_AT
        request_body = mock_request.calls[0].request.content.decode()
        assert "UPDATED_AT" in request_body

    @respx.mock
    async def test_search_orders_unauthorized_error(self, square_client: SquareClient):
        """Test handling of 401 Unauthorized error."""
        # Mock the API response
        respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(401, json={"errors": [{"code": "UNAUTHORIZED"}]})
        )

        # Call the method and expect exception
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await square_client.search_orders_by_date(
                location_ids=["loc_456"],
                target_date=date(2025, 8, 22)
            )

        assert exc_info.value.response.status_code == 401


class TestSquareClientCalculateRevenue:
    """Test cases for SquareClient.calculate_gross_revenue() method."""

    def test_calculate_revenue_basic_orders(
        self,
        mock_square_orders_response: List[Dict[str, Any]]
    ):
        """Test basic revenue calculation from orders."""
        # Create client instance (no async needed for this method)
        client = SquareClient("test_token", "test_app_id")

        # Call the method
        result = client.calculate_gross_revenue(mock_square_orders_response)

        # Assertions
        assert result["gross_sales_amount"] == 3700  # 2500 + 1200 cents
        assert result["total_discounts"] == 300      # Only first order has discount
        assert result["net_sales_amount"] == 3400    # 3700 - 300
        assert result["order_count"] == 2
        assert result["refund_count"] == 0
        assert result["currency"] == "EUR"

    def test_calculate_revenue_with_refunds(
        self,
        mock_square_orders_with_refunds: List[Dict[str, Any]]
    ):
        """Test revenue calculation with refunds."""
        client = SquareClient("test_token", "test_app_id")

        # Call the method
        result = client.calculate_gross_revenue(mock_square_orders_with_refunds)

        # Assertions
        assert result["gross_sales_amount"] == 2000  # Original order amount
        assert result["total_refunds"] == 800        # Refund amount (positive)
        assert result["net_sales_amount"] == 1200    # 2000 - 800
        assert result["order_count"] == 1
        assert result["refund_count"] == 1

    def test_calculate_revenue_empty_orders(self):
        """Test revenue calculation with empty orders list."""
        client = SquareClient("test_token", "test_app_id")

        # Call the method
        result = client.calculate_gross_revenue([])

        # Assertions
        assert result["gross_sales_amount"] == 0
        assert result["total_discounts"] == 0
        assert result["total_refunds"] == 0
        assert result["net_sales_amount"] == 0
        assert result["order_count"] == 0
        assert result["refund_count"] == 0


@pytest.mark.asyncio
class TestSquareClientGetDailyRevenue:
    """Test cases for SquareClient.get_daily_revenue() integration method."""

    @respx.mock
    async def test_get_daily_revenue_success(
        self,
        square_client: SquareClient,
        mock_square_orders_response: List[Dict[str, Any]]
    ):
        """Test complete daily revenue calculation."""
        # Mock both API calls (new sales and refunds)
        mock_response = {
            "orders": mock_square_orders_response,
            "cursor": None
        }

        # Mock new sales call (CLOSED_AT)
        respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call the method
        target_date = date(2025, 8, 22)
        result = await square_client.get_daily_revenue("loc_456", target_date)

        # Assertions
        assert result is not None
        assert result["location_id"] == "loc_456"
        assert result["date"] == "2025-08-22"
        assert result["gross_sales_amount"] == 3700
        assert result["net_sales_amount"] == 3400
        assert result["currency"] == "EUR"

    @respx.mock
    async def test_get_daily_revenue_no_orders(
        self,
        square_client: SquareClient
    ):
        """Test daily revenue with no orders."""
        # Mock empty response
        mock_response = {"orders": [], "cursor": None}
        respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call the method
        target_date = date(2025, 8, 22)
        result = await square_client.get_daily_revenue("loc_456", target_date)

        # Assertions
        assert result is not None
        assert result["net_sales_amount"] == 0
        assert result["order_count"] == 0
