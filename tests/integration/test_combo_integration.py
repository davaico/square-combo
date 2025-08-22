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
                    "id", "name", "account_id", "partner_id",
                    "snapshift_account_id", "snapshift_location_id", "teams"
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
                for loc in result:
                    print(f"  - {loc['name']} (ID: {loc['id']}) - Teams: {len(loc['teams'])}")
            else:
                print("API call successful - No locations returned (empty account)")

        except Exception as e:
            pytest.fail(f"Integration test failed: {str(e)}")

