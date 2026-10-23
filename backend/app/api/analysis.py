"""Milestone 2: run the models on a field's newest photo and lab test and save the result.

Flow:  photo (normalized) --CNN + Grad-CAM--> soil type ┐
       lab values --rating tables--> deficiencies, health score, degradation risk ├--> fusion --> `analyses` row
       lab values + soil type + crop --XGBoost + SHAP--> fertilizer signal ┘
Every part is optional: with no photo only the lab part runs, with no lab test only the photo part runs.
"""
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Response
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_analysis, owned_field
from app.config import settings
from app.db import get_db
from app.ingestion.validate import IngestError
from app.ml.loader import MODEL_VERSION, ModelRegistry, canon_class, get_registry
from app.models_db import Analysis, FarmField, SoilImage, SoilTest
from app.schemas import AnalysisOut, AnalyzeIn
from app.services import crops as crop_rules
from app.services import soil_health as sh
from app.services.storage import Storage, get_storage

router = APIRouter(tags=["analysis"])


def analysis_out(row: Analysis) -> AnalysisOut:
    return AnalysisOut(id=row.id, field_id=row.field_id, image_id=row.image_id, soil_test_id=row.soil_test_id,
                       model_version=row.model_version, created_at=row.created_at, result=row.result)


@router.get("/analysis/status")
def models_status(reg: ModelRegistry = Depends(get_registry)):
    """Which models are loaded. Handy while the model files are still being put in place."""
    body = {"image_model": reg.image_ready, "fertilizer_model": reg.fert_ready, "classes": reg.classes,
            "model_version": MODEL_VERSION, "fertilizer_options": {}}
    if reg.fert_ready:               # the values the fertilizer model accepts, for the frontend's drop-downs
        from app.ml.tabular import allowed_values
        cols = reg.fert["columns"]
        body["fertilizer_options"] = {k: allowed_values(cols, p) for k, p in
                                      (("crop_type", "Crop_Type"), ("growth_stage", "Crop_Growth_Stage"),
                                       ("season", "Season"))}
    if settings.environment != "production":
        body["errors"] = reg.errors
    return body


def _latest(db: Session, model, field_id: int):
    return db.scalars(select(model).where(model.field_id == field_id)
                      .order_by(model.created_at.desc(), model.id.desc()).limit(1)).first()


def _pick_inputs(db: Session, field: FarmField, body: AnalyzeIn) -> tuple[Optional[SoilImage], Optional[SoilTest]]:
    """A photo is analysed together with the lab test saved WITH it, never with an older sample's values.

    No ids given: the newest record decides. Newest is a photo -> that photo and its own lab test (maybe none).
    Newest is a lab test -> that test and the photo it was linked to (maybe none).
    """
    image = test = None
    if body.image_id is not None:
        image = db.get(SoilImage, body.image_id)
        if image is None or image.field_id != field.id:
            raise IngestError(422, "analysis.bad_image", "image_id does not belong to this field")
    if body.soil_test_id is not None:
        test = db.get(SoilTest, body.soil_test_id)
        if test is None or test.field_id != field.id:
            raise IngestError(422, "analysis.bad_test", "soil_test_id does not belong to this field")
    if image is None and test is None:
        newest_image, newest_test = _latest(db, SoilImage, field.id), _latest(db, SoilTest, field.id)
        if newest_image and (not newest_test or newest_image.created_at > newest_test.created_at):
            image = newest_image
        else:
            test = newest_test
    if test is None and image is not None:                       # the lab test saved with this photo
        test = db.scalars(select(SoilTest).where(SoilTest.image_id == image.id)
                          .order_by(SoilTest.id.desc()).limit(1)).first()
    if image is None and test is not None and test.image_id is not None:
        image = db.get(SoilImage, test.image_id)
    return image, test


def _soil_candidates(reg: ModelRegistry) -> set[str]:
    names = {canon_class(c) for c in reg.classes if c != "Not_Soil"}
    return names or set(sh.load_ratings()["soil_to_fertilizer_type"]) - {"_note"}


@router.post("/fields/{field_id}/analyze", response_model=AnalysisOut, status_code=201)
def analyze(body: AnalyzeIn, field: FarmField = Depends(owned_field), db: Session = Depends(get_db),
            storage: Storage = Depends(get_storage), reg: ModelRegistry = Depends(get_registry)):
    field_id = field.id
    image, test = _pick_inputs(db, field, body)
    if image is None and test is None:
        raise IngestError(422, "analysis.nothing_to_analyze", "Add a soil photo or lab values first.")
    if body.confirmed_soil_class and body.confirmed_soil_class not in _soil_candidates(reg):
        raise IngestError(422, "analysis.bad_soil_class", f"Unknown soil class '{body.confirmed_soil_class}'")

    warnings: list = []
    result: dict = {"inputs": {"image_id": image.id if image else None, "soil_test_id": test.id if test else None}}
    gradcam_png: Optional[bytes] = None

    # ---- 1. photo -> soil type (CNN + Grad-CAM)
    img_res: dict = {"available": False, "reason_key": "analysis.no_photo"}
    if image is not None:
        if not reg.image_ready:
            img_res = {"available": False, "reason_key": "analysis.models_unavailable"}
        else:
            from app.ml.image import classify_soil          # imports torch: only when a photo is analysed

            pil = ImageOps.exif_transpose(Image.open(io.BytesIO(storage.read(image.normalized_key)))).convert("RGB")
            img_res, gradcam_png = classify_soil(pil, reg)
        warnings += [{"key": k, "source": "photo"} for k in image.quality.get("warnings", [])]
    result["image"] = img_res

    # ---- 2. lab values -> ratings, deficiencies, health score
    lab = None
    findings: list[dict] = []
    if test is not None:
        values = {"nitrogen": test.nitrogen, "phosphorus": test.phosphorus, "potassium": test.potassium,
                  "ph": test.ph, "organic_matter": test.organic_matter}
        findings = sh.rate_lab(values)
        lab = {"values": {**values, "moisture": test.moisture, "tested_on": str(test.tested_on) if test.tested_on else None},
               "ratings": findings}
    result["lab"] = lab

    # ---- 3. fusion: which soil type do we trust?
    fusion: dict = {"soil_class": None, "soil_class_source": None, "notes": []}
    if body.confirmed_soil_class:
        fusion.update(soil_class=body.confirmed_soil_class, soil_class_source="user")
    elif img_res.get("tier") == "confident":
        fusion.update(soil_class=img_res["soil_class"], soil_class_source="image")
    ph = test.ph if test else None
    if img_res.get("tier") == "confirm" and not body.confirmed_soil_class:
        hint = sh.lab_ph_hint(ph, [c["soil_class"] for c in img_res["candidates"]])
        fusion["lab_hint"] = hint
        fusion["notes"].append("fusion.please_confirm_soil")
    if fusion["soil_class"] and sh.ph_matches_soil(ph, fusion["soil_class"]) is False:
        fusion["notes"].append("fusion.ph_soil_mismatch")        # photo and lab disagree: suggest re-checking one
    result["fusion"] = fusion

    # ---- 4. fertilizer model + SHAP (needs lab values, crop, stage, season)
    fert: dict = {"available": False, "reason_key": "analysis.no_lab"}
    if test is not None:
        if not reg.fert_ready:
            fert = {"available": False, "reason_key": "analysis.models_unavailable"}
        else:
            from app.ml.tabular import InputError, fertilizer_signal

            soil_map = sh.load_ratings()["soil_to_fertilizer_type"]
            try:
                fert = fertilizer_signal(
                    reg, nitrogen=test.nitrogen, phosphorus=test.phosphorus, potassium=test.potassium, ph=test.ph,
                    crop_type=body.crop_type, growth_stage=body.growth_stage, season=body.season,
                    soil_type=soil_map.get(fusion["soil_class"]) if fusion["soil_class"] else None,
                    moisture=test.moisture, organic_matter=test.organic_matter)
            except InputError as exc:
                raise IngestError(422, exc.key, exc.message)
            warnings += fert.pop("warnings", [])
    result["fertilizer_signal"] = fert

    # ---- 5. scores and diagnosis
    ml_ferts = [r["label"] for r in fert.get("recommendations", [])] if fert.get("available") else None
    result["health"] = sh.health_score(findings)
    result["degradation"] = sh.degradation_risk(findings, fusion["soil_class"])
    result["diagnosis"] = sh.diagnose(findings, ml_ferts)
    result["crops"] = (crop_rules.rank_crops(result["lab"]["values"], fusion["soil_class"]) if lab
                       else {"available": False, "reason_key": "crops.need_lab"})
    result["warnings"] = warnings

    if gradcam_png is not None:        # the heat-map is a file; the result only keeps its key (URL: /analyses/{id}/gradcam)
        key = f"analyses/{field_id}/{uuid.uuid4().hex}/gradcam.png"
        storage.save(key, gradcam_png)
        result["image"] = {**img_res, "has_gradcam": True, "gradcam_key": key}

    row = Analysis(field_id=field_id, image_id=image.id if image else None, soil_test_id=test.id if test else None,
                   result=result, model_version=MODEL_VERSION)
    db.add(row)
    db.commit()
    return analysis_out(row)


@router.get("/fields/{field_id}/analyses", response_model=list[AnalysisOut])
def list_analyses(field: FarmField = Depends(owned_field), db: Session = Depends(get_db)):
    rows = db.scalars(select(Analysis).where(Analysis.field_id == field.id)
                      .order_by(Analysis.created_at.desc(), Analysis.id.desc())).all()
    return [analysis_out(r) for r in rows]


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(row: Analysis = Depends(owned_analysis)):
    return analysis_out(row)


@router.get("/analyses/{analysis_id}/gradcam")
def get_gradcam(row: Analysis = Depends(owned_analysis), storage: Storage = Depends(get_storage)):
    key = (row.result.get("image") or {}).get("gradcam_key")
    if not key:
        raise IngestError(404, "analysis.no_gradcam", "This analysis has no heat-map.")
    return Response(storage.read(key), media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})
