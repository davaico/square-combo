"""Validated configuration shared by web onboarding and the daily task."""

import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="forbid")
    SQUARE_CLIENT_ID: str = ""
    SQUARE_CLIENT_SECRET: str = ""
    SQUARE_ENVIRONMENT: Literal["production", "sandbox"] = "production"
    SQUARE_API_VERSION: str = "2026-09-16"
    COMBO_BASE_URL: str = "https://partner.combohr.com"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'square_combo.db'}"
    APP_URL: str = "http://localhost:8000"
    HOST: str = "127.0.0.1"
    PORT: int = Field(default=8000, ge=1, le=65535)
    BUSINESS_TIMEZONE: str = "Europe/Paris"
    BUSINESS_DAY_START_HOUR: int = Field(default=6, ge=0, le=23)
    REVENUE_CURRENCY: str = "EUR"
    SYNC_DAYS_BACK: int = Field(default=1, ge=1, le=365)
    SYNC_LOOKBACK_DAYS: int = Field(default=3, ge=1, le=30)
    SYNC_LOCK_PATH: Path = BASE_DIR / "sync.lock"
    ALLOW_SINGLE_LOCATION_MAPPING: bool = False
    HTTP_TIMEOUT_SECONDS: float = Field(default=15, gt=0, le=90)
    HTTP_RETRIES: int = Field(default=2, ge=0, le=5)
    MAX_API_PAGES: int = Field(default=1000, ge=1)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    LOG_DIR: Path = BASE_DIR / "logs"
    SETUP_TTL_SECONDS: int = Field(default=600, ge=60, le=1800)

    @field_validator("BUSINESS_TIMEZONE")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("REVENUE_CURRENCY")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        if len(value) != 3 or not value.isascii() or not value.isalpha():
            raise ValueError("Use a three-letter currency code")
        if value.upper() not in {"EUR", "USD", "GBP", "CHF", "CAD", "AUD"}:
            raise ValueError(
                "This integration supports only configured currencies with two decimal places"
            )
        return value.upper()

    @field_validator("APP_URL", "COMBO_BASE_URL")
    @classmethod
    def valid_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("Use an origin URL without credentials, query or fragment")
        if parts.path not in ("", "/"):
            raise ValueError("Use an origin URL without a path")
        if parts.scheme != "https" and not (
            parts.scheme == "http" and parts.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("HTTPS is required except on loopback")
        # Browsers serialize origins with lowercase hosts and without default ports.
        # Store that same representation for OAuth, Origin checks and Secure cookies.
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parts.port
        if port is not None and port != {"http": 80, "https": 443}[parts.scheme]:
            host = f"{host}:{port}"
        return f"{parts.scheme}://{host}"

    @property
    def square_base_url(self) -> str:
        if self.SQUARE_ENVIRONMENT == "production":
            return "https://connect.squareup.com"
        return "https://connect.squareupsandbox.com"

    @property
    def secure_cookies(self) -> bool:
        return self.APP_URL.startswith("https://")


settings = Settings(_env_file=os.environ.get("SQUARE_COMBO_ENV_FILE", BASE_DIR / ".env"))
