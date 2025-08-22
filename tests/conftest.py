"""
Pytest configuration and shared fixtures.
"""

import pytest
import pytest_asyncio
import os
import logging
from typing import Dict, Any, List
from adapters.combo.client import ComboClient
from dotenv import load_dotenv
from utils.config import Settings


# Load environment variables
load_dotenv()

# Configure logging for tests
logging.basicConfig(
    # level=logging.DEBUG,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture
def test_settings():
    """Test settings with overrides for testing environment."""
    return Settings(
        COMBO_API_KEY=os.getenv("COMBO_API_KEY", "test_api_key"),
        COMBO_BASE_URL=os.getenv("COMBO_BASE_URL", "https://partner.combohr.com"),
        LOG_LEVEL="DEBUG"
    )


# ---------------------
# Combo client fixtures
# ---------------------

@pytest_asyncio.fixture
async def combo_client(test_settings):
    """Create a ComboClient instance for testing."""
    client = ComboClient(api_key=test_settings.COMBO_API_KEY)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def mock_locations_response() -> List[Dict[str, Any]]:
    """Mock response for successful get_locations API call with teams."""
    return [
        {
            "id": "loc_123",
            "name": "Downtown Location",
            "account_id": "acc_456",
            "partner_id": "partner_789",
            "snapshift_account_id": 101,
            "snapshift_location_id": 201,
            "teams": [
                {
                    "id": "team_001",
                    "name": "Morning Team"
                },
                {
                    "id": "team_002",
                    "name": "Evening Team"
                }
            ]
        },
        {
            "id": "loc_456",
            "name": "Uptown Location",
            "account_id": "acc_456",
            "partner_id": "partner_789",
            "snapshift_account_id": 101,
            "snapshift_location_id": 202,
            "teams": []
        }
    ]


@pytest.fixture
def mock_empty_locations_response() -> List[Dict[str, Any]]:
    """Mock response for empty locations list."""
    return []


@pytest.fixture
def mock_single_location_response() -> List[Dict[str, Any]]:
    """Mock response for single location without teams."""
    return [
        {
            "id": "loc_789",
            "name": "Single Location",
            "account_id": "acc_456",
            "partner_id": "partner_789",
            "snapshift_account_id": 101,
            "snapshift_location_id": 203,
            "teams": []
        }
    ]
