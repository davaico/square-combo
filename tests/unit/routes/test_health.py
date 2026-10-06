from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from database.models import SyncRun
from main import app
from utils.config import settings


def test_health_and_metrics_show_failed_and_successful_runs(db):
    with TestClient(app, base_url=settings.APP_URL) as browser:
        assert browser.get("/health").json() == {"status": "ok"}
        assert "sync_last_run_success 0" in browser.get("/metrics").text
        db.add(
            SyncRun(
                target_date=date(2026, 1, 15),
                started_at=datetime.now(UTC).replace(tzinfo=None),
                completed_at=datetime.now(UTC).replace(tzinfo=None),
                status="success",
            )
        )
        db.commit()
        assert "sync_last_run_success 1" in browser.get("/metrics").text
        db.add(
            SyncRun(
                target_date=date(2026, 1, 16),
                started_at=datetime.now(UTC).replace(tzinfo=None),
                status="failed",
                failed_clients=1,
            )
        )
        db.commit()
        metrics = browser.get("/metrics").text
        assert "sync_last_run_success 0" in metrics
        assert "sync_failed_runs_last_24h 1" in metrics
        assert "sync_last_success_timestamp_seconds 0\n" not in metrics
