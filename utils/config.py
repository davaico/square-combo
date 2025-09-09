"""
Application configuration management.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Square Configuration
    SQUARE_BASE_URL: str = "https://connect.squareup.com"
    SQUARE_CLIENT_ID: str = "sq0idp-ZoH-IKZWWKazQ6eBwQpyWw"
    SQUARE_CLIENT_SECRET: str = "sq0csp-HNIzu38p3B4_v3C6CHTF8s8x6wieLiyEQr2IsyzH6bA"
    SQUARE_ENVIRONMENT: str = "production"  # sandbox or production

    # Combo API Configuration
    COMBO_API_KEY: str = ""
    COMBO_BASE_URL: str = "https://partner.combohr.com"

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./square_combo.db"

    # Application Configuration
    LOG_LEVEL: str = "INFO"
    SYNC_TIME: str = "00:00"  # Time to run daily sync (HH:MM format)
    SYNC_DAYS_BACK: int = 1  # Number of days back to fetch revenue data

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000


# Create global settings instance
settings = Settings()
