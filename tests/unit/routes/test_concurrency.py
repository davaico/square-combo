import asyncio
from datetime import datetime

import httpx
import pytest
import respx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import Base, get_db
from database.models import Client, SetupSession
from main import app
from routes.templates import COOKIE, digest
from utils.config import settings


@pytest.fixture
def persisted_setup(tmp_path):
    # Independent SQLite connections model concurrent requests/workers, unlike StaticPool.
    engine = create_engine(f"sqlite:///{tmp_path / 'setup.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        client = Client(
            name="Cafe",
            square_merchant_id="merchant",
            square_access_token="test",
            square_refresh_token="test",
            square_access_token_expiry_date=datetime(2099, 1, 1),
        )
        db.add(client)
        db.flush()
        db.add(
            SetupSession(
                token_hash=digest("browser"),
                client_id=client.id,
                csrf_token="csrf",
                expires_at=datetime(2099, 1, 1),
            )
        )
        db.commit()

    def dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    yield factory
    app.dependency_overrides.clear()
    engine.dispose()


@respx.mock
async def test_two_simultaneous_combo_keys_have_only_one_winner(persisted_setup):
    ready = asyncio.Event()
    calls = 0

    async def validate(request):
        nonlocal calls
        calls += 1
        if calls == 2:
            ready.set()
        await asyncio.wait_for(ready.wait(), timeout=3)
        return httpx.Response(200, json=[{"id": "combo"}])

    respx.get(f"{settings.COMBO_BASE_URL}/api/v1/locations").mock(side_effect=validate)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url=settings.APP_URL, cookies={COOKIE: "browser"}
    ) as browser:
        responses = await asyncio.gather(
            *[
                browser.post(
                    "/combo",
                    data={"csrf_token": "csrf", "api_key": key},
                    headers={"Origin": settings.APP_URL},
                )
                for key in ["first-key", "second-key"]
            ]
        )
    assert sorted(response.status_code for response in responses) == [303, 409]
    winning_key = ["first-key", "second-key"][
        next(i for i, r in enumerate(responses) if r.status_code == 303)
    ]
    with persisted_setup() as db:
        assert db.query(Client).one().combo_api_key == winning_key
        assert db.query(SetupSession).count() == 0


@respx.mock
async def test_oauth_state_is_consumed_before_parallel_exchange(persisted_setup):
    with persisted_setup() as db:
        session = db.get(SetupSession, digest("browser"))
        session.client_id = None
        session.state_hash = digest("state")
        db.commit()
    exchanging = asyncio.Event()
    release = asyncio.Event()

    async def exchange(request):
        exchanging.set()
        await asyncio.wait_for(release.wait(), timeout=3)
        return httpx.Response(
            200,
            json={
                "merchant_id": "merchant",
                "access_token": "test",
                "refresh_token": "test",
                "expires_at": "2099-01-01T00:00:00Z",
            },
        )

    token = respx.post(f"{settings.square_base_url}/oauth2/token").mock(side_effect=exchange)
    respx.get(f"{settings.square_base_url}/v2/merchants/merchant").mock(
        return_value=httpx.Response(200, json={"merchant": {"business_name": "Cafe"}})
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url=settings.APP_URL, cookies={COOKIE: "browser"}
    ) as browser:
        first = asyncio.create_task(
            browser.get("/square-auth/callback", params={"state": "state", "code": "code"})
        )
        await asyncio.wait_for(exchanging.wait(), timeout=3)
        second = await browser.get(
            "/square-auth/callback", params={"state": "state", "code": "code"}
        )
        release.set()
        assert second.status_code == 403
        assert (await first).status_code == 303
    assert token.call_count == 1
