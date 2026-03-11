"""Ingest geo-dvf CSV files into raw_listings table."""

import csv
import gzip
import logging
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.engine import Engine

from src.db.client import get_session
from src.db.models import RawListing

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = {
    "id_mutation",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "adresse_numero",
    "adresse_nom_voie",
    "code_postal",
    "nom_commune",
    "code_departement",
    "code_commune",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "surface_terrain",
    "longitude",
    "latitude",
}


def validate_schema(headers: list[str]) -> None:
    """Check that expected columns are present in the CSV."""
    header_set = set(headers)
    missing = EXPECTED_COLUMNS - header_set
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")


def build_source_id(row: dict) -> str:
    """Build a composite source_id for deduplication.

    Combines id_mutation + surface + rooms to uniquely identify
    a logical apartment within a multi-lot transaction.
    """
    return f"{row['id_mutation']}|{row['surface_reelle_bati']}|{row['nombre_pieces_principales']}"


def ingest_file(engine: Engine, filepath: Path, download_date: date | None = None) -> int:
    """Ingest a single geo-dvf CSV.gz file into raw_listings.

    Returns the number of rows inserted.
    """
    download_date = download_date or date.today()
    scraped_at = datetime(download_date.year, download_date.month, download_date.day)
    inserted = 0
    skipped = 0

    with gzip.open(filepath, "rt") as f:
        reader = csv.DictReader(f)
        validate_schema(reader.fieldnames or [])

        batch: list[RawListing] = []

        for row in reader:
            # Filter: Paris apartments only
            if row.get("type_local") != "Appartement":
                continue

            source_id = build_source_id(row)

            batch.append(
                RawListing(
                    source="dvf",
                    source_id=source_id,
                    scraped_at=scraped_at,
                    raw_json=dict(row),
                )
            )

            if len(batch) >= 500:
                inserted += _flush_batch(engine, batch)
                skipped += len(batch) - inserted if not batch else 0
                batch = []

        if batch:
            inserted += _flush_batch(engine, batch)

    logger.info("Ingested %s: %d rows inserted", filepath.name, inserted)
    return inserted


def _flush_batch(engine: Engine, batch: list[RawListing]) -> int:
    """Insert a batch, skipping duplicates."""
    count = 0
    with get_session(engine) as session:
        for row in batch:
            # Check for existing entry to make re-runs idempotent
            existing = (
                session.query(RawListing)
                .filter_by(source=row.source, source_id=row.source_id, scraped_at=row.scraped_at)
                .first()
            )
            if existing is None:
                session.add(row)
                count += 1
    return count


def ingest_all(engine: Engine, data_dir: Path | None = None) -> int:
    """Ingest all DVF files found in data_dir."""
    data_dir = data_dir or Path("data/raw/dvf")
    total = 0
    for filepath in sorted(data_dir.glob("dvf_*_75.csv.gz")):
        total += ingest_file(engine, filepath)
    if total == 0:
        logger.warning("No DVF files found in %s. Run download_dvf.py first.", data_dir)
    return total
