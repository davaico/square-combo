"""
Integration tests for SquareClient making real API calls.

These tests require:
1. Valid SQUARE_ACCESS_TOKEN environment variable
2. Valid SQUARE_APPLICATION_ID environment variable
3. Network connectivity to Square API
4. Valid API credentials with appropriate permissions

Run with: pytest tests/integration/test_square_integration.py -v
"""

import pytest
import os
from datetime import date, timedelta

from adapters.square.client import SquareClient


@pytest.mark.asyncio
class TestSquareClientIntegration:
    """Integration tests for SquareClient with real API calls."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip integration tests if no API credentials are provided."""
        if not os.getenv("SQUARE_ACCESS_TOKEN") or not os.getenv("SQUARE_APPLICATION_ID"):
            pytest.skip("SQUARE_ACCESS_TOKEN and SQUARE_APPLICATION_ID environment variables not set")

    async def test_search_orders_real_api_call(self, square_client: SquareClient):
        """Test search_orders_by_date with real API call."""
        try:
            # Test with yesterday's date to ensure there might be some data
            target_date = date.today() - timedelta(days=1)

            # First, get available locations
            locations = await square_client.get_locations()
            assert locations, "No locations found for this Square account."
            location_id = locations[0]["id"]

            # Make real API call with a valid location ID
            result = await square_client.search_orders_by_date(
                location_ids=[location_id],
                target_date=target_date
            )

            # Basic assertions about response structure
            assert isinstance(result, list)

            # If orders exist, validate structure
            if result:
                order = result[0]

                # Check required fields exist
                required_fields = [
                    "id", "location_id", "state", "created_at"
                ]
                for field in required_fields:
                    assert field in order, f"Missing required field: {field}"

                # Check data types
                assert isinstance(order["id"], str)
                assert isinstance(order["location_id"], str)
                assert isinstance(order["state"], str)
                assert isinstance(order["created_at"], str)

                # If money fields exist, check their structure
                if "total_money" in order:
                    total_money = order["total_money"]
                    assert "amount" in total_money
                    assert "currency" in total_money
                    assert isinstance(total_money["amount"], int)
                    assert isinstance(total_money["currency"], str)

                print(f"Successfully fetched {len(result)} orders from Square API")
                for ord in result[:3]:  # Show first 3 orders
                    total = ord.get("total_money", {}).get("amount", 0)
                    currency = ord.get("total_money", {}).get("currency", "USD")
                    print(f"  - Order {ord['id']}: {total/100:.2f} {currency} ({ord['state']})")
            else:
                print("API call successful - No orders returned for the date")

        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")

    async def test_get_daily_revenue_real_api_call(self, square_client: SquareClient):
        """Test get_daily_revenue with real API call."""
        try:
            # Test with yesterday's date
            target_date = date.today() - timedelta(days=1)

            # First, get available locations
            locations = await square_client.get_locations()
            assert locations, "No locations found for this Square account."
            location_id = locations[0]["id"]

            # Make real API call
            result = await square_client.get_daily_revenue(location_id, target_date)

            # Basic assertions about response structure
            assert result is not None
            assert isinstance(result, dict)

            # Check required fields
            required_fields = [
                "location_id", "date", "gross_sales_amount", "total_discounts",
                "total_refunds", "net_sales_amount", "order_count", "refund_count", "currency"
            ]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            # Check data types
            assert isinstance(result["location_id"], str)
            assert isinstance(result["date"], str)
            assert isinstance(result["gross_sales_amount"], int)
            assert isinstance(result["total_discounts"], int)
            assert isinstance(result["total_refunds"], int)
            assert isinstance(result["net_sales_amount"], int)
            assert isinstance(result["order_count"], int)
            assert isinstance(result["refund_count"], int)
            assert isinstance(result["currency"], str)

            # Validate date format
            assert result["date"] == target_date.strftime("%Y-%m-%d")
            assert result["location_id"] == location_id

            # Print results
            currency = result["currency"]
            gross_sales = result["gross_sales_amount"] / 100
            discounts = result["total_discounts"] / 100
            refunds = result["total_refunds"] / 100
            net_sales = result["net_sales_amount"] / 100

            print(f"Daily Revenue for {result['date']}:")
            print(f"  Gross Sales: {gross_sales:.2f} {currency}")
            print(f"  Discounts: {discounts:.2f} {currency}")
            print(f"  Refunds: {refunds:.2f} {currency}")
            print(f"  Net Sales: {net_sales:.2f} {currency}")
            print(f"  Orders: {result['order_count']}, Refunds: {result['refund_count']}")

        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")

    async def test_french_timezone_handling(self, square_client: SquareClient):
        """Test that French timezone (GMT+2) is handled correctly."""
        try:
            # Test with a specific date
            target_date = date(2025, 8, 22)  # Fixed date for testing

            # First, get available locations
            locations = await square_client.get_locations()
            assert locations, "No locations found for this Square account."
            location_id = locations[0]["id"]

            # Make API call - this should convert to French timezone properly
            result = await square_client.search_orders_by_date(
                location_ids=[location_id],
                target_date=target_date
            )

            # The test passes if no exception is thrown
            # The actual timezone conversion is tested in unit tests
            assert isinstance(result, list)
            print(f"Timezone handling test passed - searched for orders on {target_date}")

        except Exception as e:
            # Only fail if it's not a simple "no data" case
            if "404" not in str(e) and "not found" not in str(e).lower():
                pytest.fail(f"Timezone handling test failed: {str(e)}")
            else:
                print(f"Timezone test completed (no data for test date: {target_date})")

    async def test_api_response_time(self, square_client: SquareClient):
        """Test that API response time is reasonable."""
        import time

        target_date = date.today() - timedelta(days=1)

        start_time = time.time()
        # First, get available locations
        locations = await square_client.get_locations()
        assert locations, "No locations found for this Square account."
        location_id = locations[0]["id"]

        await square_client.search_orders_by_date(
            location_ids=[location_id],
            target_date=target_date
        )
        end_time = time.time()

        response_time = end_time - start_time

        # API should respond within 10 seconds
        assert response_time < 10.0, f"API response too slow: {response_time:.2f}s"
        print(f"API response time: {response_time:.2f}s")
