"""Rotating operational logs contain IDs/counts and sanitized error classes."""

import logging.config

from utils.config import settings


def setup_logging():
    settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": str(settings.LOG_DIR / "square_combo.log"),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                },
                "sync": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "filename": str(settings.LOG_DIR / "sync.log"),
                    "maxBytes": 10485760,
                    "backupCount": 10,
                },
            },
            "root": {"level": settings.LOG_LEVEL, "handlers": ["console", "file"]},
            "loggers": {
                "tasks.sync_revenue": {
                    "level": settings.LOG_LEVEL,
                    "handlers": ["console", "sync"],
                    "propagate": False,
                },
                "httpx": {"level": "WARNING"},
                "httpx2": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
                "uvicorn.access": {"handlers": [], "propagate": False},
            },
        }
    )
