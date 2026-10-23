"""One timeline per field: photos, lab tests and (from Milestone 2) analyses, newest first."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.images import image_out
from app.api.deps import owned_field
from app.db import get_db
from app.models_db import Analysis, FarmField, SoilImage, SoilTest
from app.schemas import HistoryItem, SoilTestOut

router = APIRouter(tags=["history"])


@router.get("/fields/{field_id}/history", response_model=list[HistoryItem])
def field_history(limit: int = Query(50, ge=1, le=200), field: FarmField = Depends(owned_field),
                  db: Session = Depends(get_db)):
    field_id = field.id

    def newest(model):
        return db.scalars(select(model).where(model.field_id == field_id)
                          .order_by(model.created_at.desc(), model.id.desc()).limit(limit)).all()

    items = [HistoryItem(type="image", id=i.id, created_at=i.created_at,
                         data=image_out(i).model_dump(mode="json")) for i in newest(SoilImage)]
    items += [HistoryItem(type="soil_test", id=t.id, created_at=t.created_at,
                          data=SoilTestOut.model_validate(t).model_dump(mode="json")) for t in newest(SoilTest)]
    items += [HistoryItem(type="analysis", id=a.id, created_at=a.created_at,
                          data={"image_id": a.image_id, "soil_test_id": a.soil_test_id,
                                "model_version": a.model_version, "result": a.result}) for a in newest(Analysis)]
    items.sort(key=lambda x: (x.created_at, x.id), reverse=True)
    return items[:limit]
