"""
Soil analytics API: soil-image diagnosis (CNN + Grad-CAM) and crop / fertilizer recommendations.

Run from the project folder (the one that contains ./models):
    uvicorn soil_api:app --reload --port 8000
Interactive docs: http://localhost:8000/docs

Files expected in ./models  (override the folder with the MODEL_DIR env var):
    soil_cnn_D_hard_negatives.pt  8-class CNN checkpoint (7 soils + Not_Soil) from the Kaggle notebook;
                              set the CNN_FILE env var to use a different checkpoint
    fert_model.joblib         {"model", "label_encoder", "columns"}
    crop_model.joblib         {"model", "label_encoder", "columns"}
    inference_config.json     fertilizer defaults + training ranges (see the notebook cell)
"""
import base64
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from matplotlib import colormaps
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from torchvision import models, transforms

# --------------------------------------------------------------------------- config
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
CNN_FILE = os.getenv("CNN_FILE", "soil_cnn_D_hard_negatives.pt")   # 8 classes: 7 soils + Not_Soil
NOT_SOIL_LABEL = "Not_Soil"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]

# Image tiers, chosen on the validation set (confirmed on test). Re-tune if the CNN is retrained.
SOIL_CONFIDENT = 0.60   # >= this: show the soil type as the diagnosis
SOIL_CONFIRM = 0.40     # between CONFIRM and CONFIDENT: show top-2 and ask the farmer to confirm
# The photo is rejected as "not soil" when Not_Soil is the top class. Optionally also reject when
# P(Not_Soil) alone reaches this value (None = argmax rule only). Tune with the notebook's threshold cell.
NOT_SOIL_REJECT: Optional[float] = None
# Fertilizer: below this the answer is flagged "uncertain" in the response.
FERT_CONFIDENT = 0.60

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_SIDE_PX = 64

# Approximate agronomic mapping from the CNN's Indian soil classes to the fertilizer dataset's
# Soil_Type values. The fertilizer model barely uses Soil_Type (see its SHAP plot), so this is
# low-risk, but have it reviewed by your mentor. A soil_type sent by the user always wins.
SOIL_MAP = {
    "Alluvial": "Loamy",
    "Arid": "Sandy",
    "Black": "Clay",
    "Laterite": "Sandy",
    "Mountain": "Silt",
    "Red": "Loamy",
    "Yellow": "Loamy",
}

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
EVAL_TF = transforms.Compose([
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize(MEAN, STD),
])

state: dict = {}


# --------------------------------------------------------------------------- loading
def _require(path: Path) -> Path:
    if not path.exists():
        raise RuntimeError(f"Missing model file: {path.resolve()}")
    return path


@asynccontextmanager
async def lifespan(_app: FastAPI):
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    ckpt = torch.load(_require(MODEL_DIR / CNN_FILE), map_location="cpu", weights_only=True)
    classes = list(ckpt["classes"])
    cnn = models.efficientnet_b0(weights=None)
    cnn.classifier[1] = nn.Linear(cnn.classifier[1].in_features, len(classes))
    cnn.load_state_dict(ckpt["state_dict"])
    cnn.eval()
    state["cnn"], state["classes"] = cnn, classes
    state["not_soil_idx"] = classes.index(NOT_SOIL_LABEL) if NOT_SOIL_LABEL in classes else None

    state["fert"] = joblib.load(_require(MODEL_DIR / "fert_model.joblib"))
    state["crop"] = joblib.load(_require(MODEL_DIR / "crop_model.joblib"))
    state["cfg"] = json.loads(_require(MODEL_DIR / "inference_config.json").read_text())
    yield
    state.clear()


app = FastAPI(title="Soil Analytics API", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------- image side
def read_image(raw: bytes) -> Image.Image:
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()
        img = Image.open(io.BytesIO(raw))
    except Exception:
        raise HTTPException(400, "The uploaded file is not a readable image.")
    if img.format not in ("JPEG", "PNG"):
        raise HTTPException(415, "Only JPEG and PNG images are supported.")
    img = ImageOps.exif_transpose(img).convert("RGB")   # phone photos carry rotation in EXIF
    if min(img.size) < MIN_SIDE_PX:
        raise HTTPException(400, f"Image is too small (minimum {MIN_SIDE_PX}px on the short side).")
    img.thumbnail((1600, 1600))
    return img


def run_cnn(img: Image.Image):
    """Forward pass + Grad-CAM for the predicted class. Returns (probabilities, heatmap 224x224)."""
    cnn = state["cnn"]
    x = EVAL_TF(img).unsqueeze(0)
    a = cnn.features(x)                                    # last conv feature map (1, C, 7, 7)
    out = cnn.classifier(torch.flatten(cnn.avgpool(a), 1))
    probs = torch.softmax(out, 1)[0]
    idx = int(probs.argmax())
    g = torch.autograd.grad(out[0, idx], a)[0]             # gradient of the class score wrt feature map
    w = g.mean(dim=(2, 3), keepdim=True)
    cam = F.relu((w * a).sum(1, keepdim=True)).detach()
    cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)[0, 0].numpy()
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    return probs.detach().numpy(), cam


def overlay_png_b64(img: Image.Image, cam: np.ndarray) -> str:
    base = transforms.CenterCrop(224)(transforms.Resize(256)(img))
    heat = (colormaps["jet"](cam)[..., :3] * 255).astype(np.uint8)
    mix = (0.55 * np.asarray(base) + 0.45 * heat).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(mix).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


@app.post("/analyze-image")
def analyze_image(file: UploadFile = File(...)):
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Image is larger than 10 MB.")
    img = read_image(raw)

    probs, cam = run_cnn(img)
    classes, ns = state["classes"], state["not_soil_idx"]
    order = np.argsort(probs)[::-1]
    top = [{"soil_class": classes[i], "probability": round(float(probs[i]), 3)} for i in order[:3]]
    soil_order = [int(i) for i in order if i != ns]            # soil classes only, best first
    p_not = float(probs[ns]) if ns is not None else 0.0

    rejected = ns is not None and (order[0] == ns or (NOT_SOIL_REJECT is not None and p_not >= NOT_SOIL_REJECT))
    if rejected:
        tier, soil, message_key, shown_conf = "not_soil", None, "soil.not_soil", p_not
        candidates = []
    else:
        p1 = float(probs[soil_order[0]])
        shown_conf = p1
        if p1 >= SOIL_CONFIDENT:
            tier, soil, message_key = "confident", classes[soil_order[0]], "soil.confident"
            candidates = [{"soil_class": soil, "probability": round(p1, 3)}]
        elif p1 >= SOIL_CONFIRM:
            tier, soil, message_key = "confirm", None, "soil.confirm"      # UI shows top-2 to choose from
            candidates = [{"soil_class": classes[i], "probability": round(float(probs[i]), 3)}
                          for i in soil_order[:2]]
        else:
            tier, soil, message_key = "retake", None, "soil.retake"
            candidates = []

    return {
        "tier": tier,                             # confident | confirm | retake | not_soil
        "soil_class": soil,                       # only set when tier == "confident"
        "confidence": round(shown_conf, 3),       # for not_soil: probability of Not_Soil
        "candidates": candidates,                 # soil classes only, never Not_Soil
        "top3": top,
        "message_key": message_key,               # i18n key for next-i18next (Hindi / Kannada)
        "gradcam_png_base64": None if tier == "not_soil" else overlay_png_b64(img, cam),
        "image_info": {"width": img.size[0], "height": img.size[1]},
    }


# --------------------------------------------------------------------------- tabular side
class RecommendRequest(BaseModel):
    # needed by both models
    nitrogen: float = Field(ge=0, le=500)
    phosphorus: float = Field(ge=0, le=500)
    potassium: float = Field(ge=0, le=500)
    ph: float = Field(ge=0, le=14)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    rainfall: float = Field(ge=0, le=5000)
    # needed for the fertilizer model (crop recommendation still works without them)
    crop_type: Optional[str] = None
    growth_stage: Optional[str] = None
    season: Optional[str] = None
    # optional: filled with dataset medians / the image result when absent
    soil_type: Optional[str] = None               # Clay | Loamy | Sandy | Silt
    image_soil_class: Optional[str] = None        # e.g. "Black_Soil" from /analyze-image
    soil_moisture: Optional[float] = Field(None, ge=0, le=100)
    organic_carbon: Optional[float] = Field(None, ge=0, le=20)
    electrical_conductivity: Optional[float] = Field(None, ge=0, le=20)


def _allowed(columns: list, prefix: str) -> list:
    return sorted(c[len(prefix) + 1:] for c in columns if c.startswith(prefix + "_"))


def _match(value: str, allowed: list, field: str) -> str:
    for a in allowed:
        if a.lower() == value.strip().lower():
            return a
    raise HTTPException(422, f"Invalid {field} '{value}'. Allowed values: {allowed}")


def _top_k(model, le, X, k=3):
    p = model.predict_proba(X)[0]
    idx = np.argsort(p)[::-1][:k]
    return [{"label": str(le.classes_[i]), "probability": round(float(p[i]), 3)} for i in idx]


def _range_warnings(values: dict, ranges: dict) -> list:
    out = []
    for col, v in values.items():
        lo_hi = ranges.get(col)
        if lo_hi and not (lo_hi[0] <= v <= lo_hi[1]):
            out.append({"key": "input.out_of_training_range", "field": col, "value": v,
                        "training_range": lo_hi})
    return out


@app.post("/recommend")
def recommend(req: RecommendRequest):
    cfg, warnings = state["cfg"], []

    # ---- crop recommendation
    crop = state["crop"]
    crop_vals = {"N": req.nitrogen, "P": req.phosphorus, "K": req.potassium,
                 "temperature": req.temperature, "humidity": req.humidity,
                 "ph": req.ph, "rainfall": req.rainfall}
    X_crop = pd.DataFrame([[crop_vals[c] for c in crop["columns"]]], columns=crop["columns"]).astype(float)
    warnings += _range_warnings(crop_vals, cfg.get("ranges", {}).get("crop", {}))
    crops = [{"crop": r["label"], "probability": r["probability"]}
             for r in _top_k(crop["model"], crop["label_encoder"], X_crop)]

    # ---- fertilizer recommendation
    fert = state["fert"]
    cols = fert["columns"]
    missing = [n for n, v in [("crop_type", req.crop_type), ("growth_stage", req.growth_stage),
                              ("season", req.season)] if not v]
    if missing:
        fert_out = {"available": False, "reason_key": "fertilizer.missing_inputs", "missing": missing}
        inputs_used = {}
    else:
        defaults = cfg["fert_defaults"]
        assumed = []

        def pick(value, key):
            if value is None:
                assumed.append(key)
                return float(defaults[key])
            return float(value)

        # soil type priority: user > image result > dataset default
        soil_allowed = _allowed(cols, "Soil_Type")
        if req.soil_type:
            soil, soil_src = _match(req.soil_type, soil_allowed, "soil_type"), "user"
        elif req.image_soil_class:
            key = req.image_soil_class.replace("_Soil", "").replace("_", " ").strip().title()
            if key not in SOIL_MAP:
                raise HTTPException(422, f"Invalid image_soil_class '{req.image_soil_class}'. "
                                         f"Allowed: {sorted(SOIL_MAP)}")
            soil, soil_src = SOIL_MAP[key], "image"
        else:
            soil, soil_src = defaults["Soil_Type"], "default"
            assumed.append("Soil_Type")

        numeric = {
            "Soil_pH": req.ph,
            "Soil_Moisture": pick(req.soil_moisture, "Soil_Moisture"),
            "Organic_Carbon": pick(req.organic_carbon, "Organic_Carbon"),
            "Electrical_Conductivity": pick(req.electrical_conductivity, "Electrical_Conductivity"),
            "Nitrogen_Level": req.nitrogen, "Phosphorus_Level": req.phosphorus,
            "Potassium_Level": req.potassium, "Temperature": req.temperature,
            "Humidity": req.humidity, "Rainfall": req.rainfall,
        }
        cats = {
            "Soil_Type": soil,
            "Crop_Type": _match(req.crop_type, _allowed(cols, "Crop_Type"), "crop_type"),
            "Crop_Growth_Stage": _match(req.growth_stage, _allowed(cols, "Crop_Growth_Stage"), "growth_stage"),
            "Season": _match(req.season, _allowed(cols, "Season"), "season"),
        }
        row = {c: False for c in cols}                         # dummy columns are bool, like in training
        row.update({c: float(v) for c, v in numeric.items() if c in row})
        for prefix, val in cats.items():
            row[f"{prefix}_{val}"] = True
        X_fert = pd.DataFrame([row], columns=cols)
        warnings += _range_warnings(numeric, cfg.get("ranges", {}).get("fert", {}))

        recs = _top_k(fert["model"], fert["label_encoder"], X_fert)
        top = recs[0]
        notes = []
        if any(r["label"] == "SSP" for r in recs):
            notes.append("fertilizer.ssp_low_reliability")      # SSP had F1 0.13 in evaluation
        confident = top["probability"] >= FERT_CONFIDENT and top["label"] != "SSP"
        fert_out = {"available": True, "confident": confident, "recommendations": recs, "notes": notes}
        inputs_used = {"soil_type": soil, "soil_type_source": soil_src, "assumed_defaults": assumed}

    return {"crop_recommendations": crops, "fertilizer": fert_out,
            "inputs_used": inputs_used, "warnings": warnings}


@app.get("/health")
def health():
    return {"status": "ok", "soil_classes": state.get("classes"),
            "fertilizer_classes": [str(c) for c in state["fert"]["label_encoder"].classes_],
            "crops": len(state["crop"]["label_encoder"].classes_)}
