"""Database tables. Import everything here so Alembic and create_all see every table."""
from app.models_db.tables import Analysis, Farmer, FarmField, SoilImage, SoilTest

__all__ = ["Farmer", "FarmField", "SoilImage", "SoilTest", "Analysis"]
