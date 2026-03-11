"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.db.models import Base


@pytest.fixture
def engine():
    """In-memory SQLite engine, fresh per test."""
    eng = create_engine("sqlite:///:memory:")

    @event.listens_for(eng, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """Session that rolls back after each test."""
    with Session(engine) as s:
        yield s
