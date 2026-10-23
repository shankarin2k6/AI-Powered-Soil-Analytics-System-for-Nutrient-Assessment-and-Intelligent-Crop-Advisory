"""Crop suitability ranking from the lab values and the soil type. Pure Python, no model and no database.

For each crop in app/data/crops.json three things are checked and combined into a 0..100 score:
  1. pH       inside the crop's comfortable range = full marks, fading to zero 1.5 pH units outside it
  2. nutrients each of N, P, K compared with what the crop demands (low / medium / high)
  3. soil type well suited = full marks, fair = 0.7, anything else = 0.4 (left out when the soil type is unknown)
The crop list, ranges and weights are provisional: edit crops.json, not this file.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.services.soil_health import NPK, nutrient_score

CROPS_FILE = Path(__file__).resolve().parent.parent / "data" / "crops.json"


@lru_cache(maxsize=1)
def load_crops() -> dict:
    return json.loads(CROPS_FILE.read_text(encoding="utf-8"))


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ph_fit(ph: float, lo: float, hi: float, fade: float) -> float:
    if lo <= ph <= hi:
        return 1.0
    gap = lo - ph if ph < lo else ph - hi
    return _clip01(1 - gap / fade)


def _nutrient_fit(have: float, need: float) -> float:
    return 1.0 if have >= need else _clip01(have / need)


def rank_crops(values: dict, soil_class: Optional[str], top: int = 5) -> dict:
    """`values` uses the SoilTest column names (nitrogen, phosphorus, potassium, ph). Returns the best crops."""
    cfg = load_crops()
    ph = values.get("ph")
    if ph is None or any(values.get(n) is None for n in NPK):
        return {"available": False, "reason_key": "crops.need_lab"}
    w, demand, fade = cfg["weights"], cfg["demand_level"], cfg["ph_fade_units"]
    soil_scores = {n: nutrient_score(n, values[n]) for n in NPK}

    ranked = []
    for crop_id, c in cfg["crops"].items():
        parts = {"ph": _ph_fit(ph, c["ph"][0], c["ph"][1], fade)}
        needs = {n: demand[c[n[0]]] for n in NPK}                     # c["n"], c["p"], c["k"]
        fits = {n: _nutrient_fit(soil_scores[n], needs[n]) for n in NPK}
        parts["nutrients"] = sum(fits.values()) / len(fits)
        if soil_class:
            parts["soil_type"] = (cfg["soil_fit"]["good"] if soil_class in c["good"]
                                  else cfg["soil_fit"]["fair"] if soil_class in c["fair"] else cfg["soil_fit"]["other"])
        total_w = sum(w[k] for k in parts)
        score = round(100 * sum(w[k] / total_w * v for k, v in parts.items()), 1)

        reasons = []
        reasons.append({"key": "crops.reason.ph_ok" if parts["ph"] >= 1 else
                        ("crops.reason.ph_low" if ph < c["ph"][0] else "crops.reason.ph_high")})
        if soil_class:
            reasons.append({"key": "crops.reason.soil_good" if soil_class in c["good"] else
                            "crops.reason.soil_fair" if soil_class in c["fair"] else "crops.reason.soil_other"})
        needs_more = [n for n in NPK if fits[n] < 1.0]
        reasons += [{"key": f"crops.reason.add_{n}"} for n in needs_more]
        if not needs_more:
            reasons.append({"key": "crops.reason.nutrients_ok"})
        ranked.append({"crop": crop_id, "score": score, "reasons": reasons})

    lab = cfg["labels"]
    for r in ranked:
        r["fit"] = ("very_suitable" if r["score"] >= lab["very_suitable"] else "suitable" if r["score"] >= lab["suitable"]
                    else "possible" if r["score"] >= lab["possible"] else "poor")
        r["message_key"] = f"crops.fit.{r['fit']}"
    ranked.sort(key=lambda r: (-r["score"], r["crop"]))
    shown = [r for r in ranked if r["fit"] != "poor"][:top]
    return {"available": True, "soil_class": soil_class, "top": shown,
            "summary_key": "crops.summary" if shown else "crops.none_fit"}
