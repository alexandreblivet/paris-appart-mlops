"""CLI script to initialize the database."""

from pathlib import Path

from sqlalchemy import inspect

from src.db.client import create_db_engine, init_db


def main() -> None:
    Path("data").mkdir(exist_ok=True)
    engine = create_db_engine()
    init_db(engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Database ready. Tables: {', '.join(tables)}")


if __name__ == "__main__":
    main()
