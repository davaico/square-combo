"""Account onboarding and aggregate operational health; scheduling is external."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import Depends, FastAPI, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import SyncRun
from routes.templates import router
from utils.config import BASE_DIR, settings
from utils.dates import utc_naive
from utils.logging import setup_logging
from utils.middleware import ConfiguredHostMiddleware, RequestLimitsMiddleware


@asynccontextmanager
async def lifespan(app):
    setup_logging()
    yield


app = FastAPI(
    title="Square-Combo", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None
)
app.add_middleware(ConfiguredHostMiddleware, origin=settings.APP_URL)
app.add_middleware(RequestLimitsMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "templates"), name="static")
app.include_router(router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db.rollback()
        return Response("Database unavailable", status_code=503)
    return {"status": "ok"}


@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    latest = db.scalar(
        select(SyncRun).order_by(SyncRun.started_at.desc(), SyncRun.id.desc()).limit(1)
    )
    succeeded = db.scalar(select(func.max(SyncRun.completed_at)).where(SyncRun.status == "success"))
    failures = db.scalar(
        select(func.count())
        .select_from(SyncRun)
        .where(
            SyncRun.status == "failed",
            SyncRun.started_at >= utc_naive(datetime.now(UTC) - timedelta(days=1)),
        )
    )
    timestamp = succeeded.replace(tzinfo=UTC).timestamp() if succeeded else 0
    content = (
        "# HELP sync_last_run_success Whether the latest run completed successfully\n"
        "# TYPE sync_last_run_success gauge\n"
        f"sync_last_run_success {int(latest is not None and latest.status == 'success')}\n"
        "# HELP sync_last_success_timestamp_seconds Completion time of the last successful run\n"
        "# TYPE sync_last_success_timestamp_seconds gauge\n"
        f"sync_last_success_timestamp_seconds {timestamp}\n"
        "# HELP sync_failed_runs_last_24h Failed business-date runs in the last 24 hours\n"
        "# TYPE sync_failed_runs_last_24h gauge\n"
        f"sync_failed_runs_last_24h {failures}\n"
    )
    return Response(content, media_type="text/plain; version=0.0.4")


if __name__ == "__main__":
    import uvicorn

    # Access logs would include the OAuth callback's query code; operational logs omit URLs.
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, access_log=False)
