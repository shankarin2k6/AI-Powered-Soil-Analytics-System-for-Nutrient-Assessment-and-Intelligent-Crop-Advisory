"""Step-by-step fertiliser plan for one crop. Pure Python, no model and no database.

How the numbers are made:
  1. Start from the crop's standard dose (kg of N, P2O5, K2O per hectare, app/data/fertilizer_plans.json).
  2. Adjust each nutrient by the soil test rating: low = +25 %, medium = standard, high = -25 %.
  3. Convert to per-acre amounts of real fertilisers: DAP gives all the phosphorus (and some nitrogen), MOP gives the potash,
     urea gives the rest of the nitrogen. Each nutrient is split over the application steps listed for the crop.
  4. Add farmyard manure, lime for acidic soil and (groundnut) gypsum. Mark each step as passed / now / coming up from the crop stage.
The doses are provisional guide values: edit the JSON file, not this code.
"""
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.services.soil_health import nutrient_level, ph_level

PLANS_FILE = Path(__file__).resolve().parent.parent / "data" / "fertilizer_plans.json"
HA_TO_ACRE = 0.4047
NUTRIENT_COLUMNS = (("nitrogen", "n"), ("phosphorus", "p"), ("potassium", "k"))

# stage -> (first day, last day) of the window that counts as "now"; None = before sowing
STAGES = {"before": (None, 0), "early": (0, 30), "middle": (30, 60), "late": (60, 90)}


@lru_cache(maxsize=1)
def load_plans() -> dict:
    return json.loads(PLANS_FILE.read_text(encoding="utf-8"))


def crop_ids() -> list[str]:
    return list(load_plans()["crops"])


def _kg(x: float) -> int:
    return int(round(x))


def build_plan(crop: str, values: dict, stage: str = "before") -> dict:
    """`values` uses the SoilTest column names (nitrogen, phosphorus, potassium, ph, organic_matter); any may be missing."""
    plans = load_plans()
    spec = plans["crops"][crop]
    factors = plans["soil_test_factor"]
    prod = plans["products"]

    # ---- 1 + 2: dose per acre, adjusted by the soil test
    adjust, need = [], {}
    for column, short in NUTRIENT_COLUMNS:
        value = values.get(column)
        level = nutrient_level(column, value) if value is not None else "unknown"
        factor = factors.get(level, 1.0)
        base_ha = spec["npk"][("n", "p", "k").index(short)]
        need[short] = base_ha * factor * HA_TO_ACRE
        adjust.append({"nutrient": column, "level": level, "factor": factor})

    # ---- 3: fertilisers. DAP for P (its nitrogen counts), MOP for K, urea for the remaining N.
    dap_total = need["p"] / prod["dap"]["p"]
    n_from_dap = dap_total * prod["dap"]["n"]
    steps_spec = spec["steps"]
    dap_i = [dap_total * s["p"] for s in steps_spec]
    mop_i = [need["k"] * s["k"] / prod["mop"]["k"] for s in steps_spec]
    n_wanted = [max(0.0, need["n"] * s["n"] - dap_i[i] * prod["dap"]["n"]) for i, s in enumerate(steps_spec)]
    urea_target = max(0.0, need["n"] - n_from_dap)
    scale = urea_target / sum(n_wanted) if sum(n_wanted) > 0 else 0.0
    urea_i = [w * scale / prod["urea"]["n"] for w in n_wanted]

    # ---- 4: build the steps
    steps: list[dict] = []
    om = values.get("organic_matter")
    org = plans["organic"]
    fym = org["kg_per_acre_low_om"] if om is not None and nutrient_level("organic_matter", om) == "low" else org["kg_per_acre_default"]
    prep_items = [{"product": "fym", "kg": fym}]
    ph = values.get("ph")
    ph_state = ph_level(ph) if ph is not None else None
    if ph_state in ("acidic", "strongly_acidic"):
        prep_items.append({"product": "lime", "kg": plans["lime_kg_per_acre"][ph_state]})
    steps.append({"id": "prep", "day": -14, "title_key": "plan.step.prep", "timing_key": "plan.when.before", "how_key": "plan.how.prep",
                  "items": prep_items})

    perennial = bool(spec.get("perennial"))
    top_no = 0
    rows = []
    for i, s in enumerate(steps_spec):
        items = [{"product": p, "kg": _kg(v)} for p, v in (("dap", dap_i[i]), ("urea", urea_i[i]), ("mop", mop_i[i])) if _kg(v) >= 1]
        rows.append((s, items))
    for s, items in rows:
        if not items:
            continue
        if perennial:
            top_no += 1
            steps.append({"id": f"round{top_no}", "day": None, "title_key": "plan.step.round", "title_params": {"n": top_no},
                          "timing_key": "plan.when.start" if top_no == 1 else "plan.when.every",
                          "timing_params": {} if top_no == 1 else {"months": spec["interval_months"]},
                          "how_key": "plan.how.side", "items": items})
        elif s["day"] == 0:
            steps.append({"id": "basal", "day": 0, "title_key": "plan.step.basal", "timing_key": "plan.when.sowing",
                          "how_key": "plan.how.mix", "items": items})
        else:
            top_no += 1
            steps.append({"id": f"top{top_no}", "day": s["day"], "title_key": "plan.step.top", "title_params": {"n": top_no},
                          "timing_key": "plan.when.days", "timing_params": {"day": s["day"]},
                          "how_key": "plan.how.paddy" if spec.get("paddy") else "plan.how.side", "items": items})
    for extra in spec.get("extras", []):
        steps.append({"id": extra["product"], "day": extra["day"], "title_key": "plan.step.flowering",
                      "timing_key": "plan.when.days", "timing_params": {"day": extra["day"]}, "how_key": "plan.how.gypsum",
                      "items": [{"product": extra["product"], "kg": _kg(extra["kg_ha"] * HA_TO_ACRE)}]})
    if not perennial:
        steps.sort(key=lambda x: x["day"])

    # ---- stage: which steps are already passed, which are for now
    if stage not in STAGES:
        stage = "before"
    lo, hi = STAGES[stage]
    for st in steps:
        day = st["day"]
        if perennial or day is None:
            st["state"] = None
        elif stage == "before":                  # before sowing: preparation and the base dose come next
            st["state"] = "now" if day <= 0 else "later"
        elif day <= lo:
            st["state"] = "past"
        elif day <= hi:
            st["state"] = "now"
        else:
            st["state"] = "later"

    # ---- shopping list: everything that is not already past
    totals: dict[str, int] = {}
    for st in steps:
        if st["state"] != "past":
            for it in st["items"]:
                totals[it["product"]] = totals.get(it["product"], 0) + it["kg"]
    shopping = [{"product": p, "kg": totals[p]} for p in ("urea", "dap", "mop", "fym", "lime", "gypsum") if p in totals]

    notes = []
    if spec["group"] == "legume":
        notes.append("plan.note.legume")
    if perennial:
        notes.append("plan.note.perennial")
    if ph_state in ("acidic", "strongly_acidic"):
        notes.append("plan.note.acid")
    if ph_state in ("alkaline", "strongly_alkaline"):
        notes.append("plan.note.alkaline")
    if any(st["state"] == "past" for st in steps):
        notes.append("plan.note.past")

    return {
        "available": True, "crop": crop, "stage": stage, "unit": "acre",
        "nutrients": {"n": _kg(need["n"]), "p2o5": _kg(need["p"]), "k2o": _kg(need["k"])},
        "adjustments": adjust, "steps": steps, "shopping": shopping, "notes": notes,
    }
