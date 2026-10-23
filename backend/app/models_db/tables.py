"""The five tables of the project.

    farmers 1---* fields 1---* soil_images
                         1---* soil_tests   (lab values, optionally linked to a photo)
                         1---* analyses     (model results; filled in from Milestone 2)

Image files are not stored in the database, only their storage keys (see services/storage.py).
"""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)  # login id
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)      # optional profile details
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")   # en | hi | kn | ta
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    fields: Mapped[list["FarmField"]] = relationship(back_populates="farmer")


class FarmField(Base):
    """A farm field (named FarmField to avoid clashing with pydantic's Field)."""

    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    area_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    farmer: Mapped[Farmer] = relationship(back_populates="fields")


class SoilImage(Base):
    __tablename__ = "soil_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), index=True)

    # Storage keys of the stored files. "normalized" is what the models will use in Milestone 2.
    original_key: Mapped[str] = mapped_column(String(300))
    normalized_key: Mapped[str] = mapped_column(String(300))
    corrected_key: Mapped[str | None] = mapped_column(String(300), nullable=True)    # colour-corrected copy
    foreground_key: Mapped[str | None] = mapped_column(String(300), nullable=True)   # background removed

    width: Mapped[int] = mapped_column(Integer)           # size of the normalized image
    height: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)      # size of the uploaded file
    content_type: Mapped[str] = mapped_column(String(30))
    quality: Mapped[dict] = mapped_column(JSON, default=dict)   # blur / brightness scores + warnings
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SoilTest(Base):
    __tablename__ = "soil_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("soil_images.id"), nullable=True)

    nitrogen: Mapped[float] = mapped_column(Float)         # mg/kg
    phosphorus: Mapped[float] = mapped_column(Float)       # mg/kg
    potassium: Mapped[float] = mapped_column(Float)        # mg/kg
    ph: Mapped[float] = mapped_column(Float)
    organic_matter: Mapped[float | None] = mapped_column(Float, nullable=True)   # %
    moisture: Mapped[float | None] = mapped_column(Float, nullable=True)         # %
    tested_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Analysis(Base):
    """One model run. Empty until Milestone 2; the history endpoint already reads it."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), index=True)
    image_id: Mapped[int | None] = mapped_column(ForeignKey("soil_images.id"), nullable=True)
    soil_test_id: Mapped[int | None] = mapped_column(ForeignKey("soil_tests.id"), nullable=True)

    result: Mapped[dict] = mapped_column(JSON, default=dict)   # the full API response of the models
    model_version: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
