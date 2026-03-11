"""Thin migration wrapper.

Currently just calls create_all to initialize the schema.
When the schema stabilizes, switch to Alembic for proper migrations:
  1. alembic init alembic
  2. Configure alembic/env.py to import Base from src.db.models
  3. alembic revision --autogenerate -m "initial"
  4. alembic upgrade head
"""

from src.db.client import create_db_engine, init_db


def run_migrations(db_path: str | None = None) -> None:
    """Create all tables using create_all."""
    engine = create_db_engine(db_path)
    init_db(engine)
