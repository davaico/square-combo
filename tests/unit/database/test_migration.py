import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from database import database


def test_initialize_legacy_tables_adds_identity_constraint_and_setup_tables(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as db:
        db.execute(
            text(
                "CREATE TABLE clients (id INTEGER PRIMARY KEY, square_merchant_id VARCHAR(255) NOT NULL)"
            )
        )
        db.execute(text("INSERT INTO clients VALUES (1, 'merchant')"))
    monkeypatch.setattr(database, "engine", engine)
    database.init_db()
    database.init_db()  # Repeat provisioning is harmless.
    assert {"setup_sessions", "location_mappings", "sync_runs"}.issubset(
        inspect(engine).get_table_names()
    )
    with engine.begin() as db:
        assert db.scalar(text("SELECT square_merchant_id FROM clients WHERE id=1")) == "merchant"
        with pytest.raises(IntegrityError):
            db.execute(text("INSERT INTO clients VALUES (2, 'merchant')"))
    engine.dispose()


def test_initialize_refuses_ambiguous_legacy_identity(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'duplicates.db'}")
    with engine.begin() as db:
        db.execute(
            text(
                "CREATE TABLE clients (id INTEGER PRIMARY KEY, square_merchant_id VARCHAR(255) NOT NULL)"
            )
        )
        db.execute(text("INSERT INTO clients VALUES (1, 'merchant'), (2, 'merchant')"))
    monkeypatch.setattr(database, "engine", engine)
    with pytest.raises(IntegrityError):
        database.init_db()
    engine.dispose()
