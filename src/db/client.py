"""Database engine and session helpers."""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.db.models import Base


def get_db_url(db_path: str | None = None) -> str:
    """Build a sqlite:/// URL from a path or DATABASE_PATH env var."""
    path = db_path or os.getenv("DATABASE_PATH", "data/paris_appart.db")
    return f"sqlite:///{path}"


def create_db_engine(db_path: str | None = None, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine with SQLite pragmas (WAL, foreign_keys=ON)."""
    from sqlalchemy import create_engine

    url = get_db_url(db_path)
    engine = create_engine(url, echo=echo)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    """Create all tables defined in Base.metadata."""
    Base.metadata.create_all(engine)


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    """Context manager yielding a session with auto-commit/rollback."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
