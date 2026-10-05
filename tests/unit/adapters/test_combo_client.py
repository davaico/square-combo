"""
Unit tests for ComboClient with mocked HTTP responses.
"""

from typing import Any

import httpx
import pytest
import respx

from adapters.combo.client import ComboClient


@pytest.mark.asyncio
class TestComboClientGetLocations:
    """Test cases for ComboClient.get_locations() method."""

    @respx.mock
    async def test_get_locations_success_with_teams(
        self, combo_client: ComboClient, mock_locations_response: list[dict[str, Any]]
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
        mock_empty_locations_response: list[dict[str, Any]],
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
            return_value=httpx.Response(
                401, json={"error": "Unauthorized"}
            )  # TODO: verify error model
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
            return_value=httpx.Response(
                500, json={"error": "Internal Server Error"}
            )  # TODO: verify error model
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


@pytest.mark.asyncio
class TestComboClientPostRevenue:
    """Test cases for ComboClient.post_revenue() method."""

    @respx.mock
    async def test_post_revenue_success(self, combo_client: ComboClient):
        """Test successful revenue posting."""
        location_id = "loc_123"
        date_str = "2025-09-01"
        amount = 1500.75

        mock_response = {
            "location_id": location_id,
            "date": date_str,
            "actual_amount": amount,
            "estimated_amount": 0.0,
        }

        # Mock the API response
        mock_request = respx.post("https://partner.combohr.com/api/v1/revenues").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call the method
        result = await combo_client.post_revenue(location_id, date_str, amount)

        # Assertions
        assert result == mock_response
        assert mock_request.called
        request = mock_request.calls[0].request
        sent_payload = request.content
        import json

        assert json.loads(sent_payload) == {
            "location_id": location_id,
            "date": date_str,
            "amount": amount,
        }

    @respx.mock
    async def test_post_revenue_invalid_location(self, combo_client: ComboClient):
        """Test API error for an invalid location ID."""
        # Mock the API response for a 404 error
        respx.post("https://partner.combohr.com/api/v1/revenues").mock(
            return_value=httpx.Response(404, json={"error": "Location ID is invalid"})
        )

        # Call the method and expect an exception
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await combo_client.post_revenue("invalid_loc", "2025-09-01", 100.0)

        assert exc_info.value.response.status_code == 404

    @respx.mock
    async def test_post_revenue_validation_error(self, combo_client: ComboClient):
        """Test API error for invalid payload (e.g., missing amount)."""
        # Mock the API response for a 422 error
        respx.post("https://partner.combohr.com/api/v1/revenues").mock(
            return_value=httpx.Response(
                422,
                json={"error": "At least one of 'amount' or 'estimated amount' must be present"},
            )
        )

        # Call the method and expect an exception
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await combo_client.post_revenue("loc_123", "invalid-date", 100.0)

        assert exc_info.value.response.status_code == 422
