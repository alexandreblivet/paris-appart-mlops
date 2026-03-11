"""Database model tests."""

from datetime import datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from src.db.models import CleanListing, ModelRegistry, Prediction, RawListing


def test_all_four_tables_created(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert tables == {"raw_listings", "clean_listings", "model_registry", "predictions"}


def test_insert_read_raw_listing_with_json(session):
    listing = RawListing(
        source="seloger",
        source_id="123",
        scraped_at=datetime(2025, 1, 1),
        raw_json={"price": 500000, "rooms": 3},
    )
    session.add(listing)
    session.commit()

    result = session.query(RawListing).first()
    assert result.source == "seloger"
    assert result.raw_json["price"] == 500000


def test_raw_listing_unique_constraint(session):
    kwargs = dict(
        source="seloger",
        source_id="123",
        scraped_at=datetime(2025, 1, 1),
        raw_json={"price": 500000},
    )
    session.add(RawListing(**kwargs))
    session.commit()

    session.add(RawListing(**kwargs))
    with pytest.raises(IntegrityError):
        session.commit()


def test_insert_read_clean_listing(session):
    listing = CleanListing(
        raw_listing_id=1,
        source="seloger",
        source_id="123",
        arrondissement=7,
        price=500000,
        surface_m2=50,
        price_per_m2=10000,
    )
    session.add(listing)
    session.commit()

    result = session.query(CleanListing).first()
    assert result.price_per_m2 == 10000


def test_model_registry_is_active_query(session):
    session.add(
        ModelRegistry(
            name="xgb",
            version="1",
            artifact_path="models/v1.joblib",
            is_active=True,
        )
    )
    session.add(
        ModelRegistry(
            name="xgb",
            version="2",
            artifact_path="models/v2.joblib",
            is_active=False,
        )
    )
    session.commit()

    active = session.query(ModelRegistry).filter_by(is_active=True).all()
    assert len(active) == 1
    assert active[0].version == "1"


def test_prediction_predicted_at_auto_populated(session):
    pred = Prediction(
        model_id=1,
        clean_listing_id=1,
        predicted_price_per_m2=9500.0,
    )
    session.add(pred)
    session.commit()

    result = session.query(Prediction).first()
    assert result.predicted_at is not None


def test_session_rollback_on_exception(engine):
    from src.db.client import get_session

    with pytest.raises(ValueError):
        with get_session(engine) as s:
            s.add(
                RawListing(
                    source="test",
                    source_id="1",
                    scraped_at=datetime(2025, 1, 1),
                    raw_json={},
                )
            )
            raise ValueError("force rollback")

    # Nothing should have been committed
    from sqlalchemy.orm import Session

    with Session(engine) as s:
        assert s.query(RawListing).count() == 0
