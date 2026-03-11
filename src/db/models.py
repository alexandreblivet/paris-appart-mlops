"""SQLAlchemy 2.0 declarative models for the paris-appart pipeline."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RawListing(Base):
    """Append-only scraper output."""

    __tablename__ = "raw_listings"
    __table_args__ = (
        UniqueConstraint("source", "source_id", "scraped_at", name="uq_raw_source_id_scraped"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSON, nullable=False)


class CleanListing(Base):
    """Validated and deduplicated listings."""

    __tablename__ = "clean_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_listing_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    arrondissement: Mapped[int] = mapped_column(Integer, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    surface_m2: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_m2: Mapped[float] = mapped_column(Float, nullable=False)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    property_type: Mapped[str | None] = mapped_column(String, nullable=True)
    listing_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sale_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class ModelRegistry(Base):
    """Trained model tracking."""

    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    train_split_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class Prediction(Base):
    """Logged predictions."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(Integer, nullable=False)
    clean_listing_id: Mapped[int] = mapped_column(Integer, nullable=False)
    input_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    predicted_price_per_m2: Mapped[float] = mapped_column(Float, nullable=False)
    actual_price_per_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
