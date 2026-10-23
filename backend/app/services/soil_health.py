"""Soil health score, deficiency diagnosis, degradation risk and image + lab fusion.

Pure Python (no torch, no database), so it is fast to test and easy to change. Every cut-off and weight
lives in app/data/ratings.json; edit that file when your mentor gives you the final thresholds.

Fusion in this project is decision-level: the CNN (photo) and the lab values are analysed separately and
then combined here with explicit rules. A single neural network over image + lab features would need
photos and lab results of the SAME samples, which the public datasets do not contain.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

RATINGS_FILE = Path(__file__).resolve().parent.parent / "data" / "ratings.json"
NPK = ("nitrogen", "phosphorus", "potassium")


@lru_cache(maxsize=1)
def load_ratings() -> dict:
    return json.loads(RATINGS_FILE.read_text(encoding="utf-8"))


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


# ------------------------------------------------------------------ ratings
def nutrient_level(name: str, value: float) -> str:
    c = load_ratings()["nutrients"][name]
    return "low" if value < c["low"] else ("high" if value > c["high"] else "medium")


def nutrient_score(name: str, value: float) -> float:
    """0..1: 0.5 at the 'low' cut-off, 1.0 at the 'high' cut-off and above."""
    c = load_ratings()["nutrients"][name]
    if value < c["low"]:
        return 0.5 * _clip01(value / c["low"])
    if value >= c["high"]:
        return 1.0
    return 0.5 + 0.5 * (value - c["low"]) / (c["high"] - c["low"])


def ph_level(ph: float) -> str:
    c = load_ratings()["ph"]
    if ph < c["strongly_acidic_below"]:
        return "strongly_acidic"
    if ph < c["acidic_below"]:
        return "acidic"
    if ph > c["strongly_alkaline_above"]:
        return "strongly_alkaline"
    if ph > c["alkaline_above"]:
        return "alkaline"
    return "optimal"


def ph_score(ph: float) -> float:
    c = load_ratings()["ph"]
    lo, hi = c["optimal"]
    z_lo, z_hi = c["zero_score_at"]
    if ph < lo:
        return _clip01((ph - z_lo) / (lo - z_lo))
    if ph > hi:
        return _clip01((z_hi - ph) / (z_hi - hi))
    return 1.0


# ------------------------------------------------------------------ lab analysis
def rate_lab(test: dict) -> list[dict]:
    """One finding per measured parameter. `test` uses the SoilTest column names."""
    r = load_ratings()["nutrients"]
    out = []
    for name in (*NPK, "organic_matter"):
        v = test.get(name)
        if v is None:
            continue
        level = nutrient_level(name, v)
        out.append({"parameter": name, "value": v, "unit": r[name]["unit"], "level": level,
                    "score": round(nutrient_score(name, v), 3),
                    "message_key": f"lab.{name}.{level}"})
    ph = test.get("ph")
    if ph is not None:
        level = ph_level(ph)
        out.append({"parameter": "ph", "value": ph, "unit": "", "level": level,
                    "score": round(ph_score(ph), 3), "message_key": f"lab.ph.{level}"})
    return out


def health_score(findings: list[dict]) -> Optional[dict]:
    """Weighted mean of the parameter scores, re-weighted over what was actually measured (0..100)."""
    if not findings:
        return None
    cfg = load_ratings()
    w = cfg["weights"]
    total = sum(w[f["parameter"]] for f in findings)
    comps = [{"parameter": f["parameter"], "score": f["score"], "weight": round(w[f["parameter"]] / total, 3)}
             for f in findings]
    score = round(100 * sum(c["score"] * c["weight"] for c in comps), 1)
    g = cfg["health_grades"]
    grade = "good" if score >= g["good"] else ("moderate" if score >= g["moderate"] else "poor")
    return {"score": score, "grade": grade, "message_key": f"health.{grade}", "components": comps}


def degradation_risk(findings: list[dict], soil_class: Optional[str]) -> Optional[dict]:
    """0..100 risk index from pH stress, organic-matter depletion, NPK depletion and soil susceptibility."""
    if not findings:                 # the soil type alone says nothing about the condition of this soil
        return None
    cfg = load_ratings()["degradation"]
    by = {f["parameter"]: f["score"] for f in findings}
    parts: dict[str, float] = {}
    if "ph" in by:
        parts["ph"] = 1 - by["ph"]
    if "organic_matter" in by:
        parts["organic_matter"] = 1 - by["organic_matter"]
    npk = [by[n] for n in NPK if n in by]
    if npk:
        parts["nutrients"] = 1 - sum(npk) / len(npk)
    prior = cfg["soil_type_susceptibility"].get(soil_class) if soil_class else None
    if prior is not None:
        parts["soil_type"] = prior
    if not parts:
        return None
    w = cfg["weights"]
    total = sum(w[k] for k in parts)
    contrib = {k: w[k] / total * v for k, v in parts.items()}
    index = round(100 * sum(contrib.values()), 1)
    lv = cfg["levels"]
    level = "low" if index < lv["low"] else ("moderate" if index < lv["moderate"] else "high")
    drivers = [{"factor": k, "share": round(c / (sum(contrib.values()) or 1), 3), "message_key": f"degradation.{k}"}
               for k, c in sorted(contrib.items(), key=lambda kv: -kv[1]) if c > 0.02]
    return {"index": index, "level": level, "message_key": f"degradation.{level}", "drivers": drivers[:3]}


# ------------------------------------------------------------------ fusion
def lab_ph_hint(ph: Optional[float], candidates: list[str]) -> Optional[str]:
    """For a 'confirm' photo result: the one candidate whose typical pH range contains the lab pH, if only one does."""
    if ph is None:
        return None
    typical = load_ratings()["soil_ph_typical"]
    fits = [c for c in candidates if c in typical and typical[c][0] <= ph <= typical[c][1]]
    return fits[0] if len(fits) == 1 else None


def ph_matches_soil(ph: Optional[float], soil_class: Optional[str], slack: float = 1.0) -> Optional[bool]:
    typical = load_ratings()["soil_ph_typical"]
    if ph is None or soil_class not in typical:
        return None
    lo, hi = typical[soil_class]
    return lo - slack <= ph <= hi + slack


def diagnose(findings: list[dict], ml_fertilizers: Optional[list[str]] = None) -> dict:
    """Deficiency diagnosis from the lab ratings, cross-checked against what the fertilizer model suggests."""
    supplies = load_ratings()["fertilizer_supplies"]
    model_covers = {n for f in (ml_fertilizers or []) for n in supplies.get(f, [])}
    deficiencies = []
    for f in findings:
        if f["parameter"] in (*NPK, "organic_matter") and f["level"] == "low":
            support = ["lab"] + (["model"] if f["parameter"] in model_covers else [])
            deficiencies.append({"nutrient": f["parameter"], "value": f["value"], "unit": f["unit"],
                                 "support": support, "message_key": f"diagnosis.{f['parameter']}.low"})
    ph = next((f for f in findings if f["parameter"] == "ph"), None)
    ph_issue = None
    if ph and ph["level"] != "optimal":
        ph_issue = {"level": ph["level"], "value": ph["value"], "message_key": f"diagnosis.ph.{ph['level']}"}
    if deficiencies or ph_issue:
        summary = "diagnosis.issues_found"
    else:
        summary = "diagnosis.none_found" if findings else "diagnosis.no_lab"
    return {"deficiencies": deficiencies, "ph_issue": ph_issue, "summary_key": summary}
