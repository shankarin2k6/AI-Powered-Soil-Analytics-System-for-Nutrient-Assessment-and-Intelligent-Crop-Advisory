from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_field
from app.db import get_db
from app.models_db import Analysis, FarmField
from app.services.trend import build_trend

router = APIRouter(tags=["trend"])


@router.get("/fields/{field_id}/trend")
def field_trend(field: FarmField = Depends(owned_field), db: Session = Depends(get_db)):
    """Health score of every saved analysis, plus the direction and a rough 90-day estimate."""
    rows = db.execute(select(Analysis.id, Analysis.created_at, Analysis.result).where(Analysis.field_id == field.id)).all()
    return build_trend([(r.id, r.created_at, r.result) for r in rows])
