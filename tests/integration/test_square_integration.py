"""Opt-in read-only contract check against a dedicated Square sandbox account."""

import os

import pytest

from adapters.square.client import SquareClient


@pytest.mark.live
async def test_square_sandbox_locations():
    token = os.environ.get("SQUARE_TEST_ACCESS_TOKEN")
    if not token:
        pytest.skip("Set SQUARE_TEST_ACCESS_TOKEN for a dedicated sandbox account")
    async with SquareClient(token) as square:
        locations = await square.get_locations()
        assert all(location["status"] == "ACTIVE" for location in locations)
