import json
from datetime import date

import httpx
import pytest
import respx

from adapters.square.client import SquareClient
from utils.config import settings

BASE = "https://connect.squareupsandbox.com"
DAY = date(2026, 1, 15)


def order(id="sale", amount=900, **extra):
    return {
        "id": id,
        "state": "COMPLETED",
        "location_id": "sq",
        "closed_at": "2026-01-15T10:00:00Z",
        "total_money": {"amount": amount, "currency": "EUR"},
        "total_discount_money": {"amount": 100, "currency": "EUR"},
        **extra,
    }


def refund(id="refund", amount=200, **extra):
    return {
        "id": id,
        "location_id": "sq",
        "status": "COMPLETED",
        "created_at": "2026-01-15T12:00:00Z",
        "amount_money": {"amount": amount, "currency": "EUR"},
        **extra,
    }


@respx.mock
async def test_discount_is_not_subtracted_twice_and_order_returns_are_not_recounted(
    square_client, caplog
):
    sale = order(
        returns=[{"return_amounts": {"total_money": {"amount": 200}}}],
        customer_id="PRIVATE_SENTINEL",
    )
    search = respx.post(f"{BASE}/v2/orders/search").mock(
        return_value=httpx.Response(200, json={"orders": [sale]})
    )
    refunds = respx.get(f"{BASE}/v2/refunds").mock(
        return_value=httpx.Response(200, json={"refunds": [refund()]})
    )
    caplog.set_level("DEBUG")
    result = await square_client.get_daily_revenue("sq", DAY)
    assert result["sales_amount"] == 900
    assert result["net_sales_amount"] == 700
    assert result["total_refunds"] == 200
    assert result["refund_count"] == 1
    assert search.call_count == refunds.call_count == 1
    assert "PRIVATE_SENTINEL" not in caplog.text
    body = json.loads(search.calls[0].request.content)
    assert body["query"]["filter"]["date_time_filter"]["closed_at"] == {
        "start_at": "2026-01-15T05:00:00+00:00",
        "end_at": "2026-01-16T05:00:00+00:00",
    }
    assert body["query"]["filter"]["state_filter"] == {"states": ["COMPLETED"]}
    assert refunds.calls[0].request.url.params["status"] == "COMPLETED"


@respx.mock
async def test_distinct_refund_events_deduplicate_pages_and_ignore_old_updated_returns(
    square_client,
):
    respx.post(f"{BASE}/v2/orders/search").mock(
        side_effect=[
            httpx.Response(200, json={"orders": [order()], "cursor": "second"}),
            httpx.Response(200, json={"orders": [order()]}),
        ]
    )
    respx.get(f"{BASE}/v2/refunds").mock(
        side_effect=[
            httpx.Response(200, json={"refunds": [refund()], "cursor": "second"}),
            httpx.Response(200, json={"refunds": [refund(), refund("new", 100)]}),
        ]
    )
    result = await square_client.get_daily_revenue("sq", DAY)
    assert result["order_count"] == 1
    assert result["refund_count"] == 2
    assert result["net_sales_amount"] == 600


@respx.mock
async def test_half_open_intervals_ignore_cancelled_foreign_and_noncompleted_refunds(square_client):
    respx.post(f"{BASE}/v2/orders/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "orders": [
                    order("cancelled", state="CANCELED"),
                    order("foreign", location_id="other"),
                    order("end", closed_at="2026-01-16T05:00:00Z"),
                    order("start", closed_at="2026-01-15T05:00:00Z"),
                ]
            },
        )
    )
    respx.get(f"{BASE}/v2/refunds").mock(
        return_value=httpx.Response(
            200,
            json={
                "refunds": [
                    refund("pending", status="PENDING"),
                    refund("old", created_at="2026-01-14T12:00:00Z"),
                    refund("foreign", location_id="other"),
                ]
            },
        )
    )
    assert (await square_client.get_daily_revenue("sq", DAY))["net_sales_amount"] == 900


@pytest.mark.parametrize("sales, refunds, expected", [([], [], 0), ([], [refund()], -200)])
@respx.mock
async def test_empty_and_refund_only_days(square_client, sales, refunds, expected):
    respx.post(f"{BASE}/v2/orders/search").mock(
        return_value=httpx.Response(200, json={"orders": sales})
    )
    respx.get(f"{BASE}/v2/refunds").mock(
        return_value=httpx.Response(200, json={"refunds": refunds})
    )
    assert (await square_client.get_daily_revenue("sq", DAY))["net_sales_amount"] == expected


@pytest.mark.parametrize(
    "money",
    [
        {"amount": 10, "currency": "USD"},
        {"amount": 1.2, "currency": "EUR"},
        {"amount": True, "currency": "EUR"},
        {"amount": -1, "currency": "EUR"},
    ],
)
def test_reject_invalid_money(money):
    with pytest.raises(ValueError):
        SquareClient._money(money)


@respx.mock
async def test_repeated_cursor_and_page_cap_fail(square_client, monkeypatch):
    route = respx.post(f"{BASE}/v2/orders/search").mock(
        return_value=httpx.Response(200, json={"orders": [], "cursor": "same"})
    )
    with pytest.raises(ValueError, match="repeated"):
        await square_client.search_orders_by_date(["sq"], DAY)
    monkeypatch.setattr(settings, "MAX_API_PAGES", 1)
    route.mock(return_value=httpx.Response(200, json={"orders": [], "cursor": "more"}))
    with pytest.raises(ValueError, match="limit"):
        await square_client.search_orders_by_date(["sq"], DAY)


@respx.mock
async def test_only_active_locations_and_merchant(square_client):
    respx.get(f"{BASE}/v2/locations").mock(
        return_value=httpx.Response(
            200,
            json={
                "locations": [{"id": "yes", "status": "ACTIVE"}, {"id": "no", "status": "INACTIVE"}]
            },
        )
    )
    respx.get(f"{BASE}/v2/merchants/m").mock(
        return_value=httpx.Response(200, json={"merchant": {"business_name": "Cafe"}})
    )
    assert await square_client.get_locations() == [{"id": "yes", "status": "ACTIVE"}]
    assert (await square_client.get_merchant_by_id("m"))["business_name"] == "Cafe"


def test_conflicting_duplicates_and_naive_timestamps():
    from utils.dates import business_interval

    start, end = business_interval(DAY)
    with pytest.raises(ValueError, match="conflicting"):
        SquareClient._unique_in_interval([order(), order(amount=1000)], "closed_at", start, end)
    with pytest.raises(ValueError, match="timezone"):
        SquareClient._unique_in_interval(
            [order(closed_at="2026-01-15T12:00:00")], "closed_at", start, end
        )
