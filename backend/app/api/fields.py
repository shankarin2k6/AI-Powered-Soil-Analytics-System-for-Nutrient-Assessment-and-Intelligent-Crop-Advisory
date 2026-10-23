from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_field
from app.db import get_db
from app.models_db import Farmer, FarmField
from app.schemas import FieldCreate, FieldOut
from app.services.auth import get_current_farmer

router = APIRouter(tags=["fields"])


@router.get("/fields", response_model=list[FieldOut])
def list_my_fields(db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    return db.scalars(select(FarmField).where(FarmField.farmer_id == farmer.id).order_by(FarmField.id)).all()


@router.post("/fields", response_model=FieldOut, status_code=201)
def create_field(body: FieldCreate, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    field = FarmField(farmer_id=farmer.id, **body.model_dump())
    db.add(field)
    db.commit()
    return field


@router.get("/fields/{field_id}", response_model=FieldOut)
def get_field(field: FarmField = Depends(owned_field)):
    return field
