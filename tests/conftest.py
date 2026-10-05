"""Deterministic tests never load production dotenv files or provider credentials."""

import os
import socket
from datetime import datetime

# Settings are imported only after safe defaults are in place. No load_dotenv here.
os.environ["SQUARE_COMBO_ENV_FILE"] = os.devnull
os.environ.update(
    {
        "APP_URL": "http://localhost:8000",
        "SQUARE_ENVIRONMENT": "sandbox",
        "SQUARE_CLIENT_ID": "test-app",
        "SQUARE_CLIENT_SECRET": "test-secret",
        "DATABASE_URL": "sqlite:///:memory:",
        "HTTP_RETRIES": "0",
    }
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from adapters.combo.client import ComboClient
from adapters.square.client import SquareClient
from database.database import Base, get_db
from database.models import Client
from main import app
from utils.config import settings


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        help="Run read-only provider tests using dedicated test credentials",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker("live") and not config.getoption("--run-live"):
            item.add_marker(
                pytest.mark.skip(reason="Use --run-live for dedicated read-only provider checks")
            )


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    if request.node.get_closest_marker("live"):
        return

    def blocked(*args, **kwargs):
        raise AssertionError("Network is disabled in the default test suite")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    # Prevent developer .env files from affecting test configuration.
    monkeypatch.setattr(settings, "HTTP_RETRIES", 0)


@pytest.fixture
async def combo_client():
    async with ComboClient("test_combo_key") as client:
        yield client


@pytest.fixture
async def square_client():
    async with SquareClient("test_square_key") as client:
        yield client


@pytest.fixture
def session_factory(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    import tasks.manage as manage
    import tasks.sync_revenue as task

    monkeypatch.setattr(task, "SessionLocal", factory)
    monkeypatch.setattr(manage, "SessionLocal", factory)

    def dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def db(session_factory):
    with session_factory() as session:
        yield session


@pytest.fixture
def client_record(db):
    client = Client(
        name="Cafe",
        square_merchant_id="merchant-1",
        square_access_token="old-token",
        square_refresh_token="old-refresh",
        square_access_token_expiry_date=datetime(2099, 1, 1),
    )
    db.add(client)
    db.commit()
    return client


@pytest.fixture
def mock_locations_response():
    return [
        {
            "id": "loc_123",
            "name": "Downtown Location",
            "account_id": "acc_456",
            "partner_id": "partner_789",
            "snapshift_account_id": 101,
            "snapshift_location_id": 201,
            "teams": [
                {"id": "team_001", "name": "Morning Team"},
                {"id": "team_002", "name": "Evening Team"},
            ],
        },
        {
            "id": "loc_456",
            "name": "Uptown Location",
            "account_id": "acc_456",
            "partner_id": "partner_789",
            "snapshift_account_id": 101,
            "snapshift_location_id": 202,
            "teams": [],
        },
    ]


@pytest.fixture
def mock_empty_locations_response():
    return []
