"""
Unit tests for ComboClient with mocked HTTP responses.
"""

import pytest
import httpx
import respx
from typing import List, Dict, Any

from adapters.combo.client import ComboClient


@pytest.mark.asyncio
class TestComboClientGetLocations:
    """Test cases for ComboClient.get_locations() method."""

    @respx.mock
    async def test_get_locations_success_with_teams(
        self,
        combo_client: ComboClient,
        mock_locations_response: List[Dict[str, Any]]
    ):
        """Test successful API call returning locations with teams."""
        # Mock the API response
        respx.get("https://partner.combohr.com/api/v1/locations").mock(
            return_value=httpx.Response(200, json=mock_locations_response)
        )

        # Call the method
        result = await combo_client.get_locations()

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2

        # Check first location with teams
        first_location = result[0]
        assert first_location["id"] == "loc_123"
        assert first_location["name"] == "Downtown Location"
        assert first_location["account_id"] == "acc_456"
        assert first_location["partner_id"] == "partner_789"
        assert first_location["snapshift_account_id"] == 101
        assert first_location["snapshift_location_id"] == 201
        assert len(first_location["teams"]) == 2
        assert first_location["teams"][0]["name"] == "Morning Team"

        # Check second location without teams
        second_location = result[1]
        assert second_location["id"] == "loc_456"
        assert second_location["name"] == "Uptown Location"
        assert len(second_location["teams"]) == 0

    @respx.mock
    async def test_get_locations_success_empty_list(
        self,
        combo_client: ComboClient,
        mock_empty_locations_response: List[Dict[str, Any]]
    ):
        """Test successful API call returning empty locations list."""
        # Mock the API response
        respx.get("https://partner.combohr.com/api/v1/locations").mock(
            return_value=httpx.Response(200, json=mock_empty_locations_response)
        )

        # Call the method
        result = await combo_client.get_locations()

        # Assertions
        assert isinstance(result, list)
        assert len(result) == 0

    @respx.mock
    async def test_get_locations_unauthorized_error(self, combo_client: ComboClient):
        """Test handling of 401 Unauthorized error."""
        # Mock the API response
        respx.get("https://partner.combohr.com/api/v1/locations").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"}) # TODO: verify error model
        )

        # Call the method and expect exception
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await combo_client.get_locations()

        assert exc_info.value.response.status_code == 401

    @respx.mock
    async def test_get_locations_server_error(self, combo_client: ComboClient):
        """Test handling of 500 Server Error."""
        # Mock the API response
        respx.get("https://partner.combohr.com/api/v1/locations").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"}) # TODO: verify error model
        )

        # Call the method and expect exception
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await combo_client.get_locations()

        assert exc_info.value.response.status_code == 500

    @respx.mock
    async def test_get_locations_network_error(self, combo_client: ComboClient):
        """Test handling of network connectivity error."""
        # Mock a network error
        respx.get("https://partner.combohr.com/api/v1/locations").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        # Call the method and expect exception
        with pytest.raises(httpx.ConnectError):
            await combo_client.get_locations()

    @respx.mock
    async def test_get_locations_correct_headers_sent(self, combo_client: ComboClient):
        """Test that correct headers are sent with the request."""
        # Mock the API response
        mock_request = respx.get("https://partner.combohr.com/api/v1/locations").mock(
            return_value=httpx.Response(200, json=[])
        )

        # Call the method
        await combo_client.get_locations()

        # Check that request was made with correct headers
        assert mock_request.called
        request = mock_request.calls[0].request
        assert request.headers.get("Authorization").startswith("Bearer ")
        assert request.headers.get("Content-Type") == "application/json"
