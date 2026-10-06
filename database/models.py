"""Persistent merchant credentials, setup capabilities and sync audit records."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from database.database import Base


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    square_access_token = Column(Text, nullable=False)
    square_refresh_token = Column(Text, nullable=False)
    square_access_token_expiry_date = Column(DateTime, nullable=False)
    square_access_token_revoked = Column(Boolean, default=False, nullable=False)
    square_merchant_id = Column(String(255), nullable=False)
    combo_api_key = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


merchant_index = Index("uq_clients_merchant_id", Client.square_merchant_id, unique=True)


class SetupSession(Base):
    __tablename__ = "setup_sessions"
    token_hash = Column(String(64), primary_key=True)
    state_hash = Column(String(64))
    csrf_token = Column(String(64), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"))
    expires_at = Column(DateTime, nullable=False, index=True)


class LocationMapping(Base):
    __tablename__ = "location_mappings"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    square_location_id = Column(Text, nullable=False)
    combo_location_id = Column(Text, nullable=False)
    __table_args__ = (
        UniqueConstraint("client_id", "square_location_id"),
        UniqueConstraint("client_id", "combo_location_id"),
    )


class SyncLog(Base):
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, nullable=False)
    square_location_id = Column(Text, nullable=False)
    combo_location_id = Column(Text, nullable=False)
    square_location_name = Column(String(255))
    combo_location_name = Column(String(255))
    sync_date = Column(DateTime, nullable=False)
    revenue_amount = Column(Numeric(10, 2))
    status = Column(String(50), nullable=False)
    error_message = Column(Text)
    # Retained for old databases; new code never stores provider responses here.
    square_response = Column(Text)
    combo_response = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id = Column(Integer, primary_key=True)
    target_date = Column(Date, nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False)
    failed_clients = Column(Integer, default=0, nullable=False)
