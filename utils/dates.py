"""Business days are local calendar intervals; stored token dates are UTC."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from utils.config import settings


def utc_naive(value: str | datetime) -> datetime:
    """Keep the existing database's naive DateTime columns, always in UTC."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def business_interval(target_date: date) -> tuple[datetime, datetime]:
    zone = ZoneInfo(settings.BUSINESS_TIMEZONE)
    cutoff = time(settings.BUSINESS_DAY_START_HOUR)
    start = datetime.combine(target_date, cutoff, zone)
    end = datetime.combine(target_date + timedelta(days=1), cutoff, zone)
    return start.astimezone(UTC), end.astimezone(UTC)


def last_closed_business_day(now: datetime | None = None) -> date:
    local = (now or datetime.now(UTC)).astimezone(ZoneInfo(settings.BUSINESS_TIMEZONE))
    current = local.date()
    if local.hour < settings.BUSINESS_DAY_START_HOUR:
        current -= timedelta(days=1)
    return current - timedelta(days=settings.SYNC_DAYS_BACK)
