from fastapi import APIRouter, Depends, Query

from app.api.deps import owned_analysis
from app.ingestion.validate import IngestError
from app.models_db import Analysis
from app.services import plan as plan_service

router = APIRouter(tags=["plan"])


@router.get("/fertilizer-plan/crops")
def plan_crops():
    """Crops we have a plan for (the same ids as /crop.* in the translations)."""
    return {"crops": plan_service.crop_ids(), "stages": list(plan_service.STAGES)}


@router.get("/analyses/{analysis_id}/fertilizer-plan")
def fertilizer_plan(crop: str = Query(max_length=30), stage: str = Query("before", max_length=10),
                    row: Analysis = Depends(owned_analysis)):
    """Step-by-step plan for one crop, built from this analysis's lab values (per acre; the page scales it to the field size)."""
    if crop not in plan_service.crop_ids():
        raise IngestError(422, "plan.unknown_crop", "We do not have a plan for this crop.")
    if stage not in plan_service.STAGES:
        raise IngestError(422, "plan.unknown_stage", "Unknown crop stage.")
    lab = (row.result or {}).get("lab")
    if not lab:
        return {"available": False, "reason_key": "crops.need_lab"}
    return plan_service.build_plan(crop, lab["values"], stage)
