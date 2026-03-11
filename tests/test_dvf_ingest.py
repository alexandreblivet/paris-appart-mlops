"""Tests for DVF raw ingestion."""

import csv
import gzip
from datetime import date
from pathlib import Path

import pytest

from src.db.models import RawListing
from src.scraping.dvf_ingest import build_source_id, ingest_file, validate_schema

VALID_ROW = {
    "id_mutation": "2024-1234",
    "date_mutation": "2024-03-15",
    "nature_mutation": "Vente",
    "valeur_fonciere": "500000",
    "adresse_numero": "12",
    "adresse_nom_voie": "RUE DE RIVOLI",
    "code_postal": "75001",
    "nom_commune": "PARIS 1ER ARRONDISSEMENT",
    "code_departement": "75",
    "code_commune": "75101",
    "type_local": "Appartement",
    "surface_reelle_bati": "50.0",
    "nombre_pieces_principales": "2",
    "surface_terrain": "",
    "longitude": "2.3412",
    "latitude": "48.8606",
}


def _write_csv_gz(path: Path, rows: list[dict]) -> None:
    """Helper to write test CSV.gz files."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with gzip.open(path, "wt", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_schema_validation_passes_on_valid_row():
    validate_schema(list(VALID_ROW.keys()))


def test_schema_validation_fails_on_missing_column():
    incomplete = [k for k in VALID_ROW if k != "valeur_fonciere"]
    with pytest.raises(ValueError, match="Missing expected columns"):
        validate_schema(incomplete)


def test_source_id_construction():
    source_id = build_source_id(VALID_ROW)
    assert source_id == "2024-1234|50.0|2"


def test_ingest_file_inserts_apartments(engine, tmp_path):
    filepath = tmp_path / "dvf_2024_75.csv.gz"
    _write_csv_gz(filepath, [VALID_ROW])

    count = ingest_file(engine, filepath, download_date=date(2024, 6, 1))
    assert count == 1

    with engine.connect() as conn:
        from sqlalchemy import text

        result = conn.execute(text("SELECT count(*) FROM raw_listings")).scalar()
        assert result == 1


def test_ingest_file_skips_non_apartments(engine, tmp_path):
    filepath = tmp_path / "dvf_2024_75.csv.gz"
    non_apt = {**VALID_ROW, "type_local": "Maison"}
    _write_csv_gz(filepath, [non_apt])

    count = ingest_file(engine, filepath, download_date=date(2024, 6, 1))
    assert count == 0


def test_ingest_is_idempotent(engine, tmp_path):
    filepath = tmp_path / "dvf_2024_75.csv.gz"
    _write_csv_gz(filepath, [VALID_ROW])

    ingest_file(engine, filepath, download_date=date(2024, 6, 1))
    count = ingest_file(engine, filepath, download_date=date(2024, 6, 1))
    assert count == 0  # No new rows on re-run

    from sqlalchemy.orm import Session

    with Session(engine) as s:
        assert s.query(RawListing).count() == 1
