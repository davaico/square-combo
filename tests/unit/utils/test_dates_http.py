from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from utils.config import Settings, settings
from utils.dates import business_interval, last_closed_business_day, utc_naive
from utils.http import request_json, safe_error


@pytest.mark.parametrize(
    "day, expected, hours",
    [
        (date(2026, 1, 15), "2026-01-15T05:00:00+00:00", 24),
        (date(2026, 7, 15), "2026-07-15T04:00:00+00:00", 24),
        (date(2026, 3, 28), "2026-03-28T05:00:00+00:00", 23),
        (date(2026, 10, 24), "2026-10-24T04:00:00+00:00", 25),
    ],
)
def test_dst_intervals(day, expected, hours):
    start, end = business_interval(day)
    assert start.isoformat() == expected
    assert (end - start).total_seconds() / 3600 == hours


def test_closed_day_uses_configured_local_cutoff():
    assert last_closed_business_day(datetime(2026, 1, 16, 4, 59, tzinfo=UTC)) == date(2026, 1, 14)
    assert last_closed_business_day(datetime(2026, 1, 16, 5, tzinfo=UTC)) == date(2026, 1, 15)
    assert utc_naive("2026-01-16T07:00:00+02:00") == datetime(2026, 1, 16, 5)
    assert utc_naive(datetime(2026, 1, 16, 5)) == datetime(2026, 1, 16, 5)


@pytest.mark.parametrize(
    "values",
    [
        {"APP_URL": "http://public.example"},
        {"COMBO_BASE_URL": "https://user:pass@example.com"},
        {"APP_URL": "https://example.com/path"},
        {"APP_URL": "https://example.com?q=1"},
        {"SQUARE_ENVIRONMENT": "typo"},
        {"BUSINESS_DAY_START_HOUR": 24},
        {"REVENUE_CURRENCY": "euro"},
    ],
)
def test_invalid_config_rejected(values):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **values)


@respx.mock
async def test_rate_limit_and_transient_retry_are_bounded(monkeypatch):
    monkeypatch.setattr(settings, "HTTP_RETRIES", 2)
    sleep = AsyncMock()
    monkeypatch.setattr("utils.http.asyncio.sleep", sleep)
    route = respx.get("https://example.com/data").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "999999"}),
            httpx.Response(503, headers={"Retry-After": "invalid"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with httpx.AsyncClient() as client:
        assert await request_json(client, "GET", "https://example.com/data") == {"ok": True}
    assert route.call_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [5, 2]


@respx.mock
async def test_transport_retry_and_unsafe_oauth_not_retried(monkeypatch):
    monkeypatch.setattr(settings, "HTTP_RETRIES", 1)
    monkeypatch.setattr("utils.http.asyncio.sleep", AsyncMock())
    route = respx.post("https://example.com/token").mock(
        side_effect=[httpx.ConnectError("secret"), httpx.Response(200, json={})]
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ConnectError):
            await request_json(client, "POST", "https://example.com/token", retry_safe=False)
        assert route.call_count == 1
        route.mock(side_effect=[httpx.ConnectError("secret"), httpx.Response(200, json={"ok": 1})])
        assert await request_json(client, "POST", "https://example.com/token") == {"ok": 1}


@respx.mock
async def test_provider_error_and_permanent_failure_not_hidden(monkeypatch):
    monkeypatch.setattr(settings, "HTTP_RETRIES", 2)
    route = respx.get("https://example.com/data").mock(return_value=httpx.Response(401))
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPStatusError) as captured:
            await request_json(client, "GET", "https://example.com/data")
        assert route.call_count == 1
        assert safe_error(captured.value) == "Provider HTTP 401"
        route.mock(return_value=httpx.Response(200, json={"errors": [{"detail": "secret"}]}))
        with pytest.raises(ValueError, match="Provider reported"):
            await request_json(client, "GET", "https://example.com/data")
    assert safe_error(ValueError("secret")) == "ValueError"


@pytest.mark.parametrize(
    "configured,canonical,secure",
    [
        ("HTTPS://LOCALHOST:443/", "https://localhost", True),
        ("HTTP://LOCALHOST:80", "http://localhost", False),
        ("https://Example.COM:8443", "https://example.com:8443", True),
        ("https://caf\u00e9.example", "https://xn--caf-dma.example", True),
    ],
)
def test_origins_use_browser_canonical_form(configured, canonical, secure):
    config = Settings(_env_file=None, APP_URL=configured, COMBO_BASE_URL=configured)
    assert config.APP_URL == canonical
    assert config.COMBO_BASE_URL == canonical
    assert config.secure_cookies is secure
