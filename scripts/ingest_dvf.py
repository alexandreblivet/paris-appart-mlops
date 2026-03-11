"""CLI entry point: ingest DVF data (raw → clean)."""

import logging

from src.db.client import create_db_engine, init_db
from src.scraping.dvf_ingest import ingest_all
from src.validation.dvf_clean import clean_raw_listings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> None:
    engine = create_db_engine()
    init_db(engine)

    print("Step 1: Ingesting raw DVF files...")
    raw_count = ingest_all(engine)
    print(f"  → {raw_count} raw rows inserted")

    print("Step 2: Cleaning raw listings...")
    stats = clean_raw_listings(engine)
    print(f"  → {stats['inserted']} clean listings created")
    print(f"  → Dropped: {stats['dropped_multi_lot']} multi-lot, "
          f"{stats['dropped_outlier_price']} outlier, "
          f"{stats['dropped_not_vente']} non-vente, "
          f"{stats['dropped_parse_error']} parse errors")


if __name__ == "__main__":
    main()
