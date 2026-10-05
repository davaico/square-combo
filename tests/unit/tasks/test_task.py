import sys
from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from database.models import Client, SyncRun
from tasks import manage
from tasks import sync_revenue as task
from utils.config import settings

DAY = date(2026, 1, 15)


def new_client(db, merchant, **values):
    client = Client(
        name=merchant,
        square_merchant_id=merchant,
        square_access_token="old",
        square_refresh_token="refresh",
        square_access_token_expiry_date=datetime(2099, 1, 1),
        combo_api_key="combo",
        **values,
    )
    db.add(client)
    db.commit()
    return client


async def test_refresh_failure_does_not_stop_other_clients_and_failed_run_is_recorded(
    db, monkeypatch
):
    first, second = new_client(db, "first"), new_client(db, "second")
    first.square_access_token_expiry_date = datetime(2020, 1, 1)
    db.commit()
    refresh = AsyncMock(side_effect=RuntimeError("PRIVATE_REFRESH_SENTINEL"))
    monkeypatch.setattr(task.SetupService, "refresh_square_access_token", refresh)
    sync = AsyncMock(return_value=[{"status": "success"}])
    monkeypatch.setattr(task.SyncService, "sync_client_revenue", sync)
    assert not await task.sync_daily_revenue(DAY)
    assert sync.await_count == 1 and sync.await_args.args[0].id == second.id
    db.expire_all()
    run = db.query(SyncRun).one()
    assert run.status == "failed" and run.failed_clients == 1 and run.completed_at


async def test_expired_token_refresh_persists_rotated_credentials(db, monkeypatch):
    client = new_client(db, "merchant")
    client.square_access_token_expiry_date = datetime(2020, 1, 1)
    db.commit()
    monkeypatch.setattr(
        task.SetupService,
        "refresh_square_access_token",
        AsyncMock(
            return_value={
                "access_token": "fresh",
                "refresh_token": "rotated",
                "expires_at": "2099-01-01T02:00:00+02:00",
            }
        ),
    )
    monkeypatch.setattr(
        task.SyncService, "sync_client_revenue", AsyncMock(return_value=[{"status": "success"}])
    )
    assert await task.sync_daily_revenue(DAY)
    db.expire_all()
    assert client.square_access_token == "fresh" and client.square_refresh_token == "rotated"
    assert client.square_access_token_expiry_date == datetime(2099, 1, 1)
    assert db.query(SyncRun).one().status == "success"


@pytest.mark.parametrize("results", [[], [{"status": "failed"}], [{"status": "skipped"}]])
async def test_location_failures_are_failed_runs(db, monkeypatch, results):
    new_client(db, "merchant")
    monkeypatch.setattr(task.SyncService, "sync_client_revenue", AsyncMock(return_value=results))
    assert not await task.sync_daily_revenue(DAY)
    assert db.query(SyncRun).one().status == "failed"


async def test_future_business_day_is_rejected(session_factory):
    with pytest.raises(ValueError, match="closed"):
        await task.sync_daily_revenue(date(2099, 1, 1))


async def test_lookback_runs_all_dates_even_after_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "SYNC_LOCK_PATH", tmp_path / "sync.lock")
    monkeypatch.setattr(settings, "SYNC_LOOKBACK_DAYS", 3)
    monkeypatch.setattr(task, "last_closed_business_day", lambda: DAY)
    sync = AsyncMock(side_effect=[False, True, True])
    monkeypatch.setattr(task, "sync_daily_revenue", sync)
    assert not await task.run_dates()
    assert [call.args[0] for call in sync.await_args_list] == [
        DAY,
        date(2026, 1, 14),
        date(2026, 1, 13),
    ]
    sync.reset_mock(side_effect=True)
    sync.return_value = True
    assert await task.run_dates(DAY)
    sync.assert_awaited_once_with(DAY)


def test_lock_prevents_overlap_and_releases(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SYNC_LOCK_PATH", tmp_path / "lock")
    with task.sync_lock():
        with pytest.raises(RuntimeError, match="already"):
            with task.sync_lock():
                pytest.fail("Second lock acquired")
    with task.sync_lock():
        pass


@pytest.mark.parametrize("successful, expected", [(True, 0), (False, 1)])
def test_cli_returns_truthful_exit_code(monkeypatch, tmp_path, successful, expected):
    monkeypatch.setattr(sys, "argv", ["sync", "--date", DAY.isoformat()])
    monkeypatch.setattr(task, "run_dates", AsyncMock(return_value=successful))
    monkeypatch.setattr(task, "setup_logging", lambda: None)
    assert task.main() == expected


def test_cli_failure_is_nonzero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sync"])
    monkeypatch.setattr(task, "setup_logging", lambda: None)
    monkeypatch.setattr(task, "run_dates", AsyncMock(side_effect=RuntimeError("failure")))
    assert task.main() == 1


def test_local_admin_maps_and_deactivates(db, monkeypatch, capsys):
    client = new_client(db, "merchant")

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["manage", *args])
        manage.main()
        db.expire_all()

    run("clients")
    assert "merchant" in capsys.readouterr().out
    run("map", "--client-id", str(client.id), "--square", "s1", "--combo", "c1")
    run("map", "--client-id", str(client.id), "--square", "s1", "--combo", "c2")
    with pytest.raises(SystemExit):
        run("map", "--client-id", str(client.id), "--square", "s2", "--combo", "c2")
    run("active", "--client-id", str(client.id), "--value", "false")
    assert not client.is_active
    with pytest.raises(SystemExit):
        run("active", "--client-id", "999", "--value", "false")
