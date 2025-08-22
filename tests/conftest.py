"""
Pytest configuration and shared fixtures.
"""

import pytest
import pytest_asyncio
import os
import logging
from typing import Dict, Any, List
from adapters.combo.client import ComboClient
from adapters.square.client import SquareClient
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
        SQUARE_ACCESS_TOKEN=os.getenv("SQUARE_ACCESS_TOKEN", "test_square_token"),
        SQUARE_APPLICATION_ID=os.getenv("SQUARE_APPLICATION_ID", "test_app_id"),
        SQUARE_ENVIRONMENT=os.getenv("SQUARE_ENVIRONMENT", "sandbox"),
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


# ---------------------
# Square client fixtures
# ---------------------

@pytest_asyncio.fixture
async def square_client(test_settings, request):
    """Create a SquareClient instance for testing."""
    # Use production environment for integration tests, sandbox for unit tests
    environment = "production" if "integration" in request.node.nodeid else "sandbox"

    client = SquareClient(
        access_token=test_settings.SQUARE_ACCESS_TOKEN,
        application_id=test_settings.SQUARE_APPLICATION_ID,
        environment=environment
    )
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def mock_square_orders_response() -> List[Dict[str, Any]]:
    """Mock response for successful Square orders search."""
    return [
        {
            "id": "order_123",
            "location_id": "loc_456",
            "state": "COMPLETED",
            "created_at": "2025-08-22T10:30:00Z",
            "updated_at": "2025-08-22T10:35:00Z",
            "closed_at": "2025-08-22T10:35:00Z",
            "net_amounts": {
                "total_money": {
                    "amount": 2500,  # $25.00 in cents
                    "currency": "EUR"
                },
                "tax_money": {
                    "amount": 200,   # $2.00 tax
                    "currency": "EUR"
                },
                "discount_money": {
                    "amount": 300,   # $3.00 discount
                    "currency": "EUR"
                }
            },
            "total_money": {
                "amount": 2500,
                "currency": "EUR"
            },
            "total_tax_money": {
                "amount": 200,
                "currency": "EUR"
            },
            "total_discount_money": {
                "amount": 300,
                "currency": "EUR"
            },
            "line_items": [
                {
                    "uid": "item_1",
                    "name": "Coffee",
                    "quantity": "2",
                    "total_money": {
                        "amount": 1600,
                        "currency": "EUR"
                    },
                    "total_discount_money": {
                        "amount": 200,
                        "currency": "EUR"
                    }
                },
                {
                    "uid": "item_2", 
                    "name": "Pastry",
                    "quantity": "1",
                    "total_money": {
                        "amount": 900,
                        "currency": "EUR"
                    },
                    "total_discount_money": {
                        "amount": 100,
                        "currency": "EUR"
                    }
                }
            ]
        },
        {
            "id": "order_456",
            "location_id": "loc_456",
            "state": "COMPLETED",
            "created_at": "2025-08-22T14:15:00Z",
            "updated_at": "2025-08-22T14:20:00Z",
            "closed_at": "2025-08-22T14:20:00Z",
            "net_amounts": {
                "total_money": {
                    "amount": 1200,  # $12.00
                    "currency": "EUR"
                }
            },
            "total_money": {
                "amount": 1200,
                "currency": "EUR"
            },
            "total_tax_money": {
                "amount": 100,
                "currency": "EUR"
            },
            "line_items": [
                {
                    "uid": "item_3",
                    "name": "Sandwich",
                    "quantity": "1",
                    "total_money": {
                        "amount": 1200,
                        "currency": "EUR"
                    }
                }
            ]
        }
    ]


@pytest.fixture
def mock_square_orders_with_refunds() -> List[Dict[str, Any]]:
    """Mock response for Square orders with refunds."""
    return [
        {
            "id": "order_789",
            "location_id": "loc_456",
            "state": "COMPLETED",
            "created_at": "2025-08-21T16:00:00Z",
            "updated_at": "2025-08-22T11:00:00Z",  # Updated today due to refund
            "closed_at": "2025-08-21T16:05:00Z",
            "total_money": {
                "amount": 2000,
                "currency": "EUR"
            },
            "returns": [
                {
                    "uid": "return_1",
                    "created_at": "2025-08-22T11:00:00Z",  # Refund processed today
                    "return_line_items": [
                        {
                            "uid": "return_item_1",
                            "name": "Coffee",
                            "quantity": "1",
                            "total_money": {
                                "amount": -800,  # Negative for refund
                                "currency": "EUR"
                            }
                        }
                    ],
                    "return_amounts": {
                        "total_money": {
                            "amount": -800,
                            "currency": "EUR"
                        }
                    }
                }
            ]
        }
    ]


@pytest.fixture
def mock_square_empty_orders() -> List[Dict[str, Any]]:
    """Mock response for empty orders list."""
    return []


@pytest.fixture
def mock_square_search_response() -> Dict[str, Any]:
    """Mock response wrapper for Square orders search API."""
    return {
        "orders": [],  # Will be populated by specific test
        "cursor": None
    }


@pytest.fixture
def mock_square_paginated_response() -> Dict[str, Any]:
    """Mock response with pagination cursor."""
    return {
        "orders": [],  # Will be populated by specific test
        "cursor": "next_page_cursor_123"
    }
