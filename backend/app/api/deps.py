"""Shared dependencies: look up a record and make sure it belongs to the signed-in farmer.

Records of other farmers answer 404 (not 403), so nobody can find out which ids exist.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models_db import Analysis, Farmer, FarmField, SoilImage, SoilTest
from app.services.auth import get_current_farmer


def owned_field(field_id: int, db: Session = Depends(get_db),
                farmer: Farmer = Depends(get_current_farmer)) -> FarmField:
    field = db.get(FarmField, field_id)
    if field is None or field.farmer_id != farmer.id:
        raise HTTPException(404, "Field not found")
    return field


def owned_image(image_id: int, db: Session = Depends(get_db),
                farmer: Farmer = Depends(get_current_farmer)) -> SoilImage:
    image = db.get(SoilImage, image_id)
    field = db.get(FarmField, image.field_id) if image else None
    if image is None or field is None or field.farmer_id != farmer.id:
        raise HTTPException(404, "Image not found")
    return image


def owned_soil_test(test_id: int, db: Session = Depends(get_db),
                    farmer: Farmer = Depends(get_current_farmer)) -> SoilTest:
    test = db.get(SoilTest, test_id)
    field = db.get(FarmField, test.field_id) if test else None
    if test is None or field is None or field.farmer_id != farmer.id:
        raise HTTPException(404, "Soil test not found")
    return test


def owned_analysis(analysis_id: int, db: Session = Depends(get_db),
                   farmer: Farmer = Depends(get_current_farmer)) -> Analysis:
    row = db.get(Analysis, analysis_id)
    field = db.get(FarmField, row.field_id) if row else None
    if row is None or field is None or field.farmer_id != farmer.id:
        raise HTTPException(404, "Analysis not found")
    return row
