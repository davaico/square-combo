"""
Application configuration management.
"""
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Square Configuration
    SQUARE_BASE_URL: str = "https://connect.squareup.com"
    SQUARE_CLIENT_ID: str = ""
    SQUARE_CLIENT_SECRET: str = ""
    SQUARE_ENVIRONMENT: str = "production"  # sandbox or production

    # Combo API Configuration
    COMBO_API_KEY: str = ""
    COMBO_BASE_URL: str = "https://partner.combohr.com"

    # Database Configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'square_combo.db'}"

    # Application Configuration
    LOG_LEVEL: str = "INFO"
    SYNC_TIME: str = "00:00"  # Time to run daily sync (HH:MM format)
    SYNC_DAYS_BACK: int = 1  # Number of days back to fetch revenue data

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000


# Create global settings instance
settings = Settings()
