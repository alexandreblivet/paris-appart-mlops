"""Tests for DVF cleaning pipeline."""

from datetime import datetime

from src.db.models import RawListing
from src.validation.dvf_clean import (
    build_address,
    clean_raw_listings,
    extract_arrondissement,
    parse_date,
)


def _insert_raw(session, raw_json: dict, source_id: str | None = None) -> RawListing:
    """Helper to insert a raw listing."""
    mutation_id = raw_json.get("id_mutation", "mut-1")
    raw = RawListing(
        source="dvf",
        source_id=source_id or f"{mutation_id}|50.0|2",
        scraped_at=datetime(2024, 6, 1),
        raw_json=raw_json,
    )
    session.add(raw)
    session.commit()
    return raw


VALID_JSON = {
    "id_mutation": "2024-1234",
    "date_mutation": "2024-03-15",
    "nature_mutation": "Vente",
    "valeur_fonciere": "500000",
    "adresse_numero": "12",
    "adresse_nom_voie": "RUE DE RIVOLI",
    "code_postal": "75001",
    "code_commune": "75101",
    "type_local": "Appartement",
    "surface_reelle_bati": "50.0",
    "nombre_pieces_principales": "2",
    "longitude": "2.3412",
    "latitude": "48.8606",
}


def test_parse_valid_apartment_row(engine, session):
    _insert_raw(session, VALID_JSON)
    stats = clean_raw_listings(engine)
    assert stats["inserted"] == 1

    with engine.connect() as conn:
        from sqlalchemy import text

        row = conn.execute(text("SELECT * FROM clean_listings")).fetchone()
        assert row is not None


def test_drops_non_vente(engine, session):
    data = {**VALID_JSON, "nature_mutation": "Adjudication"}
    _insert_raw(session, data)
    stats = clean_raw_listings(engine)
    assert stats["inserted"] == 0
    assert stats["dropped_not_vente"] >= 1


def test_dedup_multi_row_same_surface(engine, session):
    """Two rows with same id_mutation and same surface → one clean listing."""
    _insert_raw(session, VALID_JSON, source_id="2024-1234|50.0|2")
    _insert_raw(session, VALID_JSON, source_id="2024-1234|50.0|2-dup")
    stats = clean_raw_listings(engine)
    assert stats["inserted"] == 1


def test_drops_multi_row_different_surfaces(engine, session):
    """Two rows with same id_mutation but different surfaces → dropped."""
    row1 = {**VALID_JSON, "surface_reelle_bati": "50.0"}
    row2 = {**VALID_JSON, "surface_reelle_bati": "75.0"}
    _insert_raw(session, row1, source_id="2024-1234|50.0|2")
    _insert_raw(session, row2, source_id="2024-1234|75.0|3")
    stats = clean_raw_listings(engine)
    assert stats["inserted"] == 0
    assert stats["dropped_multi_lot"] >= 1


def test_drops_below_min_surface(engine, session):
    data = {**VALID_JSON, "surface_reelle_bati": "8", "id_mutation": "small"}
    _insert_raw(session, data, source_id="small|8|1")
    stats = clean_raw_listings(engine)
    assert stats["dropped_min_surface"] >= 1


def test_drops_below_min_price_per_m2(engine, session):
    # 10000 / 50 = 200 €/m2 — way too low
    data = {**VALID_JSON, "valeur_fonciere": "10000", "id_mutation": "cheap"}
    _insert_raw(session, data, source_id="cheap|50.0|2")
    stats = clean_raw_listings(engine)
    assert stats["dropped_outlier_price"] >= 1


def test_drops_above_max_price_per_m2(engine, session):
    # 2000000 / 50 = 40000 €/m2 — outlier
    data = {**VALID_JSON, "valeur_fonciere": "2000000", "id_mutation": "expensive"}
    _insert_raw(session, data, source_id="expensive|50.0|2")
    stats = clean_raw_listings(engine)
    assert stats["dropped_outlier_price"] >= 1


def test_arrondissement_extraction():
    assert extract_arrondissement("75103") == 3
    assert extract_arrondissement("75120") == 20
    assert extract_arrondissement("75100") is None  # 0 is not valid
    assert extract_arrondissement(None) is None


def test_date_parsing():
    result = parse_date("2024-01-04")
    assert result == datetime(2024, 1, 4)
    assert parse_date("") is None
    assert parse_date(None) is None


def test_address_building():
    row = {"adresse_numero": "12", "adresse_nom_voie": "RUE DE RIVOLI", "code_postal": "75001"}
    assert build_address(row) == "12 RUE DE RIVOLI 75001"


def test_clean_is_idempotent(engine, session):
    _insert_raw(session, VALID_JSON)
    clean_raw_listings(engine)
    stats = clean_raw_listings(engine)
    assert stats["inserted"] == 0
    assert stats["dropped_duplicate"] == 1
