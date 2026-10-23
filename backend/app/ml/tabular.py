"""Fertilizer model (XGBoost) with a per-prediction explanation.

The explanation is TreeSHAP computed by XGBoost itself (`pred_contribs=True`), so no extra library is needed
and it matches the global SHAP plots from the training notebook. One-hot columns are merged back into the
feature they came from (Crop_Type_Wheat + Crop_Type_Rice ... -> Crop_Type) so farmers see 5 short lines.
"""
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb

from app.ml.loader import ModelRegistry

FERT_CONFIDENT = 0.60
CATEGORICAL = ("Soil_Type", "Crop_Type", "Crop_Growth_Stage", "Season")


class InputError(ValueError):
    """The caller sent a value the model does not know. `key` is an i18n message key."""

    def __init__(self, key: str, message: str):
        super().__init__(message)
        self.key, self.message = key, message


def allowed_values(columns: list, prefix: str) -> list:
    return sorted(c[len(prefix) + 1:] for c in columns if c.startswith(prefix + "_"))


def _match(value: str, allowed: list, field: str) -> str:
    for a in allowed:
        if a.lower() == value.strip().lower():
            return a
    raise InputError("input.invalid_value", f"Invalid {field} '{value}'. Allowed values: {allowed}")


def _range_warnings(values: dict, ranges: dict) -> list:
    return [{"key": "input.out_of_training_range", "field": c, "value": v, "training_range": ranges[c]}
            for c, v in values.items() if c in ranges and not (ranges[c][0] <= v <= ranges[c][1])]


def _group(feature: str) -> str:
    for prefix in CATEGORICAL:
        if feature.startswith(prefix + "_"):
            return prefix
    return feature


def fertilizer_signal(reg: ModelRegistry, *, nitrogen: float, phosphorus: float, potassium: float, ph: float,
                      crop_type: Optional[str], growth_stage: Optional[str], season: Optional[str],
                      soil_type: Optional[str], moisture: Optional[float] = None,
                      organic_matter: Optional[float] = None) -> dict:
    """Top-3 fertilizers plus the features that drove the top one. Never raises for missing optional inputs."""
    missing = [n for n, v in (("crop_type", crop_type), ("growth_stage", growth_stage), ("season", season)) if not v]
    if missing:
        return {"available": False, "reason_key": "fertilizer.missing_inputs", "missing": missing}

    fert, cfg = reg.fert, reg.cfg
    cols, defaults = fert["columns"], cfg["fert_defaults"]
    assumed: list[str] = []

    def pick(value, key):
        if value is None:
            assumed.append(key)
            return float(defaults[key])
        return float(value)

    soil = _match(soil_type, allowed_values(cols, "Soil_Type"), "soil_type") if soil_type else defaults["Soil_Type"]
    if not soil_type:
        assumed.append("Soil_Type")
    numeric = {
        "Soil_pH": ph, "Nitrogen_Level": nitrogen, "Phosphorus_Level": phosphorus, "Potassium_Level": potassium,
        "Soil_Moisture": pick(moisture, "Soil_Moisture"),
        "Organic_Carbon": pick(None if organic_matter is None else organic_matter / 1.724, "Organic_Carbon"),
        "Electrical_Conductivity": pick(None, "Electrical_Conductivity"),
    }
    cats = {"Soil_Type": soil,
            "Crop_Type": _match(crop_type, allowed_values(cols, "Crop_Type"), "crop_type"),
            "Crop_Growth_Stage": _match(growth_stage, allowed_values(cols, "Crop_Growth_Stage"), "growth_stage"),
            "Season": _match(season, allowed_values(cols, "Season"), "season")}
    row = {c: False for c in cols}                              # dummy columns are bool, like in training
    row.update({c: float(v) for c, v in numeric.items() if c in row})
    for prefix, val in cats.items():
        row[f"{prefix}_{val}"] = True
    X = pd.DataFrame([row], columns=cols)

    model, le = fert["model"], fert["label_encoder"]
    p = model.predict_proba(X)[0]
    idx = np.argsort(p)[::-1][:3]
    recs = [{"label": str(le.classes_[i]), "probability": round(float(p[i]), 3)} for i in idx]
    notes = ["fertilizer.ssp_low_reliability"] if any(r["label"] == "SSP" for r in recs) else []
    confident = recs[0]["probability"] >= FERT_CONFIDENT and recs[0]["label"] != "SSP"

    return {"available": True, "confident": confident, "recommendations": recs, "notes": notes,
            "explanation": _explain(model, X, int(idx[0]), recs[0]["label"]),
            "inputs_used": {"soil_type": soil, "assumed_defaults": assumed},
            "warnings": _range_warnings({**numeric}, cfg.get("ranges", {}).get("fert", {}))}


def _explain(model, X: pd.DataFrame, class_index: int, label: str, top: int = 5) -> dict:
    """Top features pushing the model toward (or away from) the recommended fertilizer."""
    contribs = model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    c = np.asarray(contribs)[0]
    c = c[class_index] if c.ndim == 2 else c                   # (classes, features + 1) for multiclass
    grouped: dict[str, float] = {}
    for name, value in zip(X.columns, c[:-1]):                 # the last entry is the bias term
        grouped[_group(name)] = grouped.get(_group(name), 0.0) + float(value)
    ranked = sorted(grouped.items(), key=lambda kv: -abs(kv[1]))[:top]
    return {"for": label, "method": "treeshap",
            "features": [{"feature": k, "contribution": round(v, 3), "direction": "towards" if v >= 0 else "away"}
                         for k, v in ranked]}
