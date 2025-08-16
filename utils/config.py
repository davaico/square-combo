"""
Application configuration management.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Square API Configuration
    SQUARE_APPLICATION_ID: str = ""
    SQUARE_ACCESS_TOKEN: str = ""
    SQUARE_ENVIRONMENT: str = "sandbox"  # sandbox or production

    # Combo API Configuration
    COMBO_API_KEY: str = ""
    COMBO_BASE_URL: str = "https://api.combo.com"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./square_combo.db"

    # Application Configuration
    LOG_LEVEL: str = "INFO"
    SYNC_TIME: str = "00:00"  # Time to run daily sync (HH:MM format)
    SYNC_DAYS_BACK: int = 1  # Number of days back to fetch revenue data

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create global settings instance
settings = Settings()
