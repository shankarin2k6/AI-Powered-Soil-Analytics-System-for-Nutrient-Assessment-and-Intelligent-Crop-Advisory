from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_field, owned_soil_test
from app.db import get_db
from app.models_db import FarmField, SoilImage, SoilTest
from app.schemas import SoilTestCreate, SoilTestOut, SoilTestUpdate

router = APIRouter(tags=["soil tests"])


@router.post("/fields/{field_id}/soil-tests", response_model=SoilTestOut, status_code=201)
def create_soil_test(body: SoilTestCreate, field: FarmField = Depends(owned_field), db: Session = Depends(get_db)):
    field_id = field.id
    if body.image_id is not None:
        image = db.get(SoilImage, body.image_id)
        if not image or image.field_id != field_id:
            raise HTTPException(422, "image_id does not belong to this field")
    test = SoilTest(field_id=field_id, **body.model_dump())
    db.add(test)
    db.commit()
    return test


@router.get("/fields/{field_id}/soil-tests", response_model=list[SoilTestOut])
def list_soil_tests(field: FarmField = Depends(owned_field), db: Session = Depends(get_db)):
    return db.scalars(select(SoilTest).where(SoilTest.field_id == field.id)
                      .order_by(SoilTest.created_at.desc(), SoilTest.id.desc())).all()


@router.get("/soil-tests/{test_id}", response_model=SoilTestOut)
def get_soil_test(test: SoilTest = Depends(owned_soil_test)):
    return test


@router.put("/soil-tests/{test_id}", response_model=SoilTestOut)
def update_soil_test(body: SoilTestUpdate, test: SoilTest = Depends(owned_soil_test), db: Session = Depends(get_db)):
    for name, value in body.model_dump().items():
        setattr(test, name, value)
    db.commit()
    return test
