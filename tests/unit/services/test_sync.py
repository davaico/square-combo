from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import httpx
import pytest
import respx
from sqlalchemy.exc import SQLAlchemyError

from database.models import Client, LocationMapping, SyncLog
from services.client_service import ClientService
from services.sync_service import MappingError, SyncService
from utils.config import settings

DAY = date(2026, 1, 15)
LOCATION = {
    "square_location_id": "sq",
    "combo_location_id": "cb",
    "square_location_name": "Cafe",
    "combo_location_name": "Cafe",
}


def test_inactive_revoked_empty_clients_are_not_eligible(db, client_record):
    client_record.combo_api_key = "key"
    db.commit()
    service = ClientService(db)
    assert service.get_all_active_clients() == [client_record]
    for field, value in [
        ("is_active", False),
        ("square_access_token_revoked", True),
        ("combo_api_key", ""),
    ]:
        before = getattr(client_record, field)
        setattr(client_record, field, value)
        db.commit()
        assert service.get_all_active_clients() == []
        setattr(client_record, field, before)
        db.commit()
    client_record.combo_api_key = None
    db.commit()
    assert service.get_all_active_clients() == []
    assert service.get_client_by_id(9999) is None
    assert service.get_client_by_merchant_id("missing") is None


def test_names_are_unique_complete_and_singleton_policy_explicit(db, monkeypatch):
    service = SyncService(db)
    assert (
        service.map_square_combo_locations(
            [{"id": "s", "name": " Cafe "}], [{"id": "c", "name": "CAFE"}]
        )[0]["combo_location_id"]
        == "c"
    )
    bad = [
        ([], [{"id": "c"}]),
        ([{"id": "s", "name": "Cafe"}], []),
        ([{"id": "s", "name": "Cafe"}], [{"id": "c", "name": "Other"}]),
        (
            [{"id": "s", "name": "Cafe"}],
            [{"id": "c1", "name": "Cafe"}, {"id": "c2", "name": "CAFE"}],
        ),
        (
            [{"id": "s1", "name": "Cafe"}, {"id": "s2", "name": "Cafe"}],
            [{"id": "c", "name": "Cafe"}],
        ),
        (
            [{"id": "s", "name": "Cafe"}, {"id": "s", "name": "Other"}],
            [{"id": "c", "name": "Cafe"}],
        ),
        ([{"id": "s"}], [{"id": "c"}]),
    ]
    for square, combo in bad:
        with pytest.raises(MappingError):
            service.map_square_combo_locations(square, combo)
    monkeypatch.setattr(settings, "ALLOW_SINGLE_LOCATION_MAPPING", True)
    assert (
        service.map_square_combo_locations([{"id": "s"}], [{"id": "c"}])[0]["combo_location_id"]
        == "c"
    )


def test_explicit_mapping_avoids_name_ambiguity_and_rejects_stale_ids(db, client_record):
    mapping = LocationMapping(
        client_id=client_record.id, square_location_id="s", combo_location_id="c2"
    )
    db.add(mapping)
    db.commit()
    service = SyncService(db)
    assert (
        service.map_square_combo_locations(
            [{"id": "s", "name": "Cafe"}],
            [{"id": "c1", "name": "Cafe"}, {"id": "c2", "name": "Cafe"}],
            client_record.id,
        )[0]["combo_location_id"]
        == "c2"
    )
    with pytest.raises(MappingError, match="unavailable"):
        service.map_square_combo_locations([{"id": "s"}], [{"id": "other"}], client_record.id)


@pytest.mark.parametrize("minor", [0, 123, -500])
async def test_zero_negative_and_positive_are_posted(db, minor):
    square, combo = AsyncMock(), AsyncMock()
    square.get_daily_revenue.return_value = {"net_sales_amount": minor, "currency": "EUR"}
    result = await SyncService(db).sync_location_revenue(square, combo, LOCATION, DAY)
    amount = Decimal(minor) / 100
    combo.post_revenue.assert_awaited_once_with("cb", DAY.isoformat(), amount)
    assert result == {"status": "success", "posted_revenue": amount}


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"net_sales_amount": 1.2, "currency": "EUR"},
        {"net_sales_amount": 10, "currency": "USD"},
        {"net_sales_amount": 10**10, "currency": "EUR"},
    ],
)
async def test_missing_or_invalid_data_never_overwrites_combo(db, data):
    square, combo = AsyncMock(), AsyncMock()
    square.get_daily_revenue.return_value = data
    assert (await SyncService(db).sync_location_revenue(square, combo, LOCATION, DAY))[
        "status"
    ] == "failed"
    combo.post_revenue.assert_not_awaited()


@respx.mock
async def test_client_flow_logs_posted_zero_and_closes_clients(db, client_record):
    client_record.combo_api_key = "key"
    db.commit()
    respx.get("https://connect.squareupsandbox.com/v2/locations").mock(
        return_value=httpx.Response(
            200, json={"locations": [{"id": "sq", "name": "Cafe", "status": "ACTIVE"}]}
        )
    )
    respx.get("https://partner.combohr.com/api/v1/locations").mock(
        return_value=httpx.Response(200, json=[{"id": "cb", "name": "Cafe"}])
    )
    respx.post("https://connect.squareupsandbox.com/v2/orders/search").mock(
        return_value=httpx.Response(200, json={"orders": []})
    )
    respx.get("https://connect.squareupsandbox.com/v2/refunds").mock(
        return_value=httpx.Response(200, json={"refunds": []})
    )
    post = respx.post("https://partner.combohr.com/api/v1/revenues").mock(
        return_value=httpx.Response(200, json={"actual_amount": 0})
    )
    results = await SyncService(db).sync_client_revenue(client_record, DAY)
    assert results[0]["status"] == "success" and post.call_count == 1
    assert db.query(SyncLog).one().revenue_amount == 0
    assert db.query(SyncLog).one().square_response is None


async def test_failed_audit_rolls_back_and_session_is_reusable(db, client_record, monkeypatch):
    service = SyncService(db)
    original = db.commit
    monkeypatch.setattr(
        db, "commit", lambda: (_ for _ in ()).throw(SQLAlchemyError("PRIVATE_SENTINEL"))
    )
    with pytest.raises(SQLAlchemyError):
        service.create_sync_log(
            client_record.id, LOCATION, DAY, {"status": "success", "posted_revenue": Decimal(1)}
        )
    monkeypatch.setattr(db, "commit", original)
    assert db.query(Client).count() == 1
    assert db.query(SyncLog).count() == 0
    service.create_sync_log(
        client_record.id, LOCATION, DAY, {"status": "failed", "error": "Provider HTTP 500"}
    )
    assert db.query(SyncLog).one().status == "failed"


@respx.mock
async def test_mapping_failure_makes_no_revenue_calls(db, client_record):
    client_record.combo_api_key = "key"
    db.commit()
    respx.get("https://connect.squareupsandbox.com/v2/locations").mock(
        return_value=httpx.Response(200, json={"locations": []})
    )
    respx.get("https://partner.combohr.com/api/v1/locations").mock(
        return_value=httpx.Response(200, json=[])
    )
    assert (await SyncService(db).sync_client_revenue(client_record, DAY))[0]["status"] == "failed"
    assert len(respx.calls) == 2
