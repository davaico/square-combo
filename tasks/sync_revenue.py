"""Scheduled synchronization, with isolated client failures and truthful exit status."""

import argparse
import asyncio
import fcntl
import logging
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta

from database.database import SessionLocal
from database.models import Client, SyncRun
from services.client_service import ClientService
from services.setup_service import SetupService
from services.sync_service import SyncService
from utils.config import settings
from utils.dates import business_interval, last_closed_business_day, utc_naive
from utils.http import safe_error
from utils.logging import setup_logging

logger = logging.getLogger(__name__)


@contextmanager
def sync_lock():
    settings.SYNC_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with settings.SYNC_LOCK_PATH.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another sync is already running") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def sync_daily_revenue(target_date: date | None = None) -> bool:
    target_date = target_date or last_closed_business_day()
    if business_interval(target_date)[1] > datetime.now(UTC):
        raise ValueError("Only closed business days can be synchronized")
    started = utc_naive(datetime.now(UTC))
    with SessionLocal() as db:
        run = SyncRun(target_date=target_date, started_at=started, status="running")
        db.add(run)
        db.commit()
        run_id = run.id
        client_ids = [client.id for client in ClientService(db).get_all_active_clients()]
    failed = 0
    try:
        for client_id in client_ids:
            with SessionLocal() as db:
                client = db.get(Client, client_id)
                try:
                    if (
                        not client
                        or not client.is_active
                        or client.square_access_token_revoked
                        or not client.combo_api_key
                    ):
                        continue  # operator may deactivate after selection
                    if client.square_access_token_expiry_date <= utc_naive(
                        datetime.now(UTC) + timedelta(minutes=5)
                    ):
                        token = await SetupService().refresh_square_access_token(
                            client.square_refresh_token
                        )
                        ClientService(db).save_refreshed_token(client, token)
                    results = await SyncService(db).sync_client_revenue(client, target_date)
                    if not results or any(result["status"] != "success" for result in results):
                        failed += 1
                        logger.warning("Client %d failed on %s", client_id, target_date)
                    else:
                        logger.info("Client %d synchronized on %s", client_id, target_date)
                except Exception as error:
                    db.rollback()
                    failed += 1
                    logger.warning("Client %d failed: %s", client_id, safe_error(error))
    except BaseException:
        failed += 1
        raise
    finally:
        with SessionLocal() as db:
            run = db.get(SyncRun, run_id)
            run.completed_at = utc_naive(datetime.now(UTC))
            run.status = "failed" if failed else "success"
            run.failed_clients = failed
            db.commit()
    return failed == 0


async def run_dates(target_date: date | None = None) -> bool:
    with sync_lock():
        dates = (
            [target_date]
            if target_date
            else [
                last_closed_business_day() - timedelta(days=offset)
                for offset in range(settings.SYNC_LOOKBACK_DAYS)
            ]
        )
        successful = True
        for day in dates:
            successful = await sync_daily_revenue(day) and successful
        return successful


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Closed business date YYYY-MM-DD; otherwise reconcile the configured lookback",
    )
    args = parser.parse_args()
    setup_logging()
    try:
        return 0 if asyncio.run(run_dates(args.date)) else 1
    except Exception as error:
        logger.error("Sync could not complete: %s", safe_error(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
