"""
Integration tests for ComboClient making real API calls.

These tests require:
1. Valid COMBO_API_KEY environment variable
2. Network connectivity to partner.combohr.com
3. Valid API credentials

Run with: pytest tests/integration/ -v
"""

import pytest
import os
from datetime import date

from adapters.combo.client import ComboClient


@pytest.mark.asyncio
class TestComboClientIntegration:
    """Integration tests for ComboClient with real API calls."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Skip integration tests if no API key is provided."""
        if not os.getenv("COMBO_API_KEY"):
            pytest.skip("COMBO_API_KEY environment variable not set")

    async def test_get_locations_real_api_call(self, combo_client: ComboClient):
        """Test get_locations with real API call."""
        try:
            # Make real API call
            result = await combo_client.get_locations()

            # Basic assertions about response structure
            assert isinstance(result, list)

            # If locations exist, validate structure
            if result:
                location = result[0]

                # Check required fields exist
                required_fields = [
                    "id",
                    "name",
                    "account_id",
                    "partner_id",
                    "snapshift_account_id",
                    "snapshift_location_id",
                    "teams",
                ]
                for field in required_fields:
                    assert field in location, f"Missing required field: {field}"

                # Check data types
                assert isinstance(location["id"], str)
                assert isinstance(location["name"], str)
                assert isinstance(location["account_id"], str)
                assert isinstance(location["partner_id"], str)
                assert isinstance(location["snapshift_account_id"], int)
                assert isinstance(location["snapshift_location_id"], int)
                assert isinstance(location["teams"], list)

                # If teams exist, check their structure
                if location["teams"]:
                    team = location["teams"][0]
                    assert "id" in team
                    assert "name" in team
                    assert isinstance(team["id"], str)
                    assert isinstance(team["name"], str)

                print(f"Successfully fetched {len(result)} locations from Combo API")
                print(f"Result: \n {result}")
            else:
                print("API call successful - No locations returned (empty account)")

        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")

    async def test_post_revenue_real_api_call(self, combo_client: ComboClient):
        """Test post_revenue with a real API call."""
        try:
            # First, get a valid location ID to post to
            locations = await combo_client.get_locations()
            if not locations:
                pytest.skip("No locations found in Combo account to post revenue to.")

            location_id = locations[0]["id"]
            target_date = date.today().strftime("%Y-%m-%d")
            amount = 99.99  # A test amount

            # Make the real API call
            result = await combo_client.post_revenue(location_id, target_date, amount)

            # Assertions
            assert result is not None
            assert isinstance(result, dict)
            assert result.get("location_id") is not None
            assert result.get("date") == target_date
            assert result.get("actual_amount") == amount

            print(
                f"Successfully posted revenue of {amount} to location {location_id} on {target_date}"
            )

        except Exception as e:
            pytest.fail(f"Integration test for post_revenue failed: {str(e)}")
