"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from utils.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=({"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}),
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create base class for models
class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Import all models here to ensure they are registered with SQLAlchemy
    from . import models  # noqa

    Base.metadata.create_all(bind=engine)
    # create_all does not add new indexes to tables from older releases.
    models.merchant_index.create(bind=engine, checkfirst=True)
