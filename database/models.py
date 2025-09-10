"""
Database models for Square-Combo integration.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric
from sqlalchemy.sql import func

from .database import Base


class Client(Base):
    """Client model to store client information and API credentials."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    square_access_token = Column(Text, nullable=False)
    square_refresh_token = Column(Text, nullable=False)
    square_access_token_expiry_date = Column(DateTime, nullable=False)
    square_access_token_revoked = Column(Boolean, default=False)
    square_merchant_id = Column(String(255), nullable=False)
    combo_api_key = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Location(Base):
    """Location model to store Square location information."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=False)  # Foreign key to Client
    square_location_id = Column(String(255), nullable=False, unique=True)
    combo_location_id = Column(String(255), nullable=True)  # May be mapped later
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SyncLog(Base):
    """Sync log model to track daily revenue sync operations."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=False)
    location_id = Column(Integer, nullable=False)
    sync_date = Column(DateTime(timezone=True), nullable=False)  # Date of revenue data
    revenue_amount = Column(Numeric(10, 2), nullable=True)  # Amount synced
    status = Column(String(50), nullable=False)  # success, failed, pending
    error_message = Column(Text, nullable=True)
    square_response = Column(Text, nullable=True)  # JSON response from Square
    combo_response = Column(Text, nullable=True)  # JSON response from Combo
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
