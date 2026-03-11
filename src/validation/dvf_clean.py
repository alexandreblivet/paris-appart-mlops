"""Clean raw DVF listings into clean_listings table."""

import logging
from datetime import datetime

from sqlalchemy.engine import Engine

from src.db.client import get_session
from src.db.models import CleanListing, RawListing

logger = logging.getLogger(__name__)

# Outlier thresholds
MIN_SURFACE_M2 = 9  # Legal minimum habitable surface in France
MIN_PRICE_PER_M2 = 2_000
MAX_PRICE_PER_M2 = 25_000


def parse_float(val: str | None) -> float | None:
    """Parse a string to float, returning None on failure."""
    if not val or val.strip() == "":
        return None
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return None


def parse_int(val: str | None) -> int | None:
    """Parse a string to int, returning None on failure."""
    f = parse_float(val)
    return int(f) if f is not None else None


def parse_date(val: str | None) -> datetime | None:
    """Parse YYYY-MM-DD date string."""
    if not val or val.strip() == "":
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d")
    except ValueError:
        return None


def extract_arrondissement(code_commune: str | None) -> int | None:
    """Extract arrondissement from code_commune (e.g. '75103' -> 3)."""
    if not code_commune or len(code_commune) < 3:
        return None
    try:
        arr = int(code_commune[-2:])
        return arr if 1 <= arr <= 20 else None
    except ValueError:
        return None


def build_address(row: dict) -> str | None:
    """Build address string from DVF fields."""
    numero = row.get("adresse_numero", "").strip()
    voie = row.get("adresse_nom_voie", "").strip()
    code_postal = row.get("code_postal", "").strip()
    if not voie:
        return None
    parts = [numero, voie, code_postal]
    return " ".join(p for p in parts if p)


def clean_raw_listings(engine: Engine) -> dict[str, int]:
    """Process unprocessed raw DVF listings into clean_listings.

    Returns a dict of counts: inserted, dropped_* reasons.
    """
    stats = {
        "total_raw": 0,
        "dropped_not_vente": 0,
        "dropped_multi_lot": 0,
        "dropped_parse_error": 0,
        "dropped_min_surface": 0,
        "dropped_outlier_price": 0,
        "dropped_no_arrondissement": 0,
        "dropped_duplicate": 0,
        "inserted": 0,
    }

    with get_session(engine) as session:
        # Get all raw DVF listings
        raw_listings = session.query(RawListing).filter_by(source="dvf").all()
        stats["total_raw"] = len(raw_listings)

        # Find already-processed source_ids
        existing_ids = set(
            row[0]
            for row in session.query(CleanListing.source_id).filter_by(source="dvf").all()
        )

        # Group by id_mutation for multi-row dedup
        mutations: dict[str, list[RawListing]] = {}
        for raw in raw_listings:
            data = raw.raw_json
            mutation_id = data.get("id_mutation", "")
            mutations.setdefault(mutation_id, []).append(raw)

        for mutation_id, rows in mutations.items():
            # Filter: only Vente (standard sales)
            vente_rows = [
                r for r in rows if r.raw_json.get("nature_mutation") == "Vente"
            ]
            stats["dropped_not_vente"] += len(rows) - len(vente_rows)

            if not vente_rows:
                continue

            # Multi-row dedup: check if surfaces differ
            surfaces = {parse_float(r.raw_json.get("surface_reelle_bati")) for r in vente_rows}
            surfaces.discard(None)

            if len(surfaces) > 1:
                # Different apartments in same transaction — can't split price
                stats["dropped_multi_lot"] += len(vente_rows)
                continue

            # Take first row (duplicates from land×culture cross-product)
            raw = vente_rows[0]
            data = raw.raw_json

            # Skip already processed
            if mutation_id in existing_ids:
                stats["dropped_duplicate"] += 1
                continue

            # Parse fields
            price = parse_float(data.get("valeur_fonciere"))
            surface = parse_float(data.get("surface_reelle_bati"))
            if price is None or surface is None or surface == 0:
                stats["dropped_parse_error"] += 1
                continue

            if surface < MIN_SURFACE_M2:
                stats["dropped_min_surface"] += 1
                continue

            price_per_m2 = price / surface
            if price_per_m2 < MIN_PRICE_PER_M2 or price_per_m2 > MAX_PRICE_PER_M2:
                stats["dropped_outlier_price"] += 1
                continue

            arrondissement = extract_arrondissement(data.get("code_commune"))
            if arrondissement is None:
                stats["dropped_no_arrondissement"] += 1
                continue

            clean = CleanListing(
                raw_listing_id=raw.id,
                source="dvf",
                source_id=mutation_id,
                arrondissement=arrondissement,
                latitude=parse_float(data.get("latitude")),
                longitude=parse_float(data.get("longitude")),
                address=build_address(data),
                price=price,
                surface_m2=surface,
                price_per_m2=price_per_m2,
                rooms=parse_int(data.get("nombre_pieces_principales")),
                property_type="appartement",
                listing_date=None,
                sale_date=parse_date(data.get("date_mutation")),
            )
            session.add(clean)
            stats["inserted"] += 1

    for key, val in stats.items():
        logger.info("DVF clean — %s: %d", key, val)
    return stats
