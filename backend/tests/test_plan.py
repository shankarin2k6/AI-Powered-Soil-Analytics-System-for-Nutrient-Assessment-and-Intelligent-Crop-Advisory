"""Milestone 3: step-by-step fertiliser plan."""
import pytest

from app.services import crops as crop_rules
from app.services import plan
from tests.test_analysis import add_photo, add_test, analyze, registries, use  # noqa: F401  (helpers + fixtures)

API = "/api/v1"
MEDIUM = {"nitrogen": 180, "phosphorus": 15, "potassium": 80, "ph": 6.8, "organic_matter": 1.0}
LOW = {**MEDIUM, "nitrogen": 60, "phosphorus": 4, "potassium": 20}
HIGH = {**MEDIUM, "nitrogen": 300, "phosphorus": 40, "potassium": 160}


def amount(p, product, states=("past", "now", "later", None)):
    return sum(i["kg"] for s in p["steps"] if s["state"] in states for i in s["items"] if i["product"] == product)


def test_plan_file_matches_the_crop_list_and_splits_add_up():
    data = plan.load_plans()["crops"]
    assert set(data) == set(crop_rules.load_crops()["crops"])                     # every crop ranked has a plan and vice versa
    for cid, c in data.items():
        for key in "npk":
            assert sum(s[key] for s in c["steps"]) == pytest.approx(1.0), (cid, key)
        assert len(c["npk"]) == 3 and all(v >= 0 for v in c["npk"])


@pytest.mark.parametrize("crop", plan.crop_ids())
def test_every_crop_builds_a_sensible_plan(crop):
    p = plan.build_plan(crop, MEDIUM, "before")
    assert p["available"] and p["steps"][0]["id"] == "prep"
    for st in p["steps"]:
        assert st["items"] and all(i["kg"] >= 1 for i in st["items"])
    assert amount(p, "urea") >= 0 and any(s["product"] == "fym" for s in p["shopping"])


def test_nutrients_delivered_match_the_dose():
    p = plan.build_plan("rice", MEDIUM, "before")                                 # 120-60-60 per ha = about 49-24-24 per acre
    assert (p["nutrients"]["n"], p["nutrients"]["p2o5"], p["nutrients"]["k2o"]) == (49, 24, 24)
    n = amount(p, "urea") * 0.46 + amount(p, "dap") * 0.18
    assert n == pytest.approx(49, abs=3)
    assert amount(p, "dap") * 0.46 == pytest.approx(24, abs=2)
    assert amount(p, "mop") * 0.60 == pytest.approx(24, abs=2)


def test_soil_test_raises_or_lowers_the_dose():
    low, med, high = (plan.build_plan("wheat", v) for v in (LOW, MEDIUM, HIGH))
    assert low["nutrients"]["n"] > med["nutrients"]["n"] > high["nutrients"]["n"]
    assert amount(low, "urea") > amount(med, "urea") > amount(high, "urea")
    assert {a["level"] for a in low["adjustments"]} == {"low"}
    unknown = plan.build_plan("wheat", {"ph": 6.8})
    assert unknown["nutrients"] == med["nutrients"] and unknown["adjustments"][0]["level"] == "unknown"


def test_legumes_need_little_urea_and_groundnut_gets_gypsum():
    soy, rice = plan.build_plan("soybean", MEDIUM), plan.build_plan("rice", MEDIUM)
    assert amount(soy, "urea") < amount(rice, "urea") / 3 and "plan.note.legume" in soy["notes"]
    gn = plan.build_plan("groundnut", MEDIUM)
    assert any(s["id"] == "gypsum" for s in gn["steps"]) and amount(gn, "gypsum") > 100


def test_ph_and_organic_matter_extras():
    acid = plan.build_plan("maize", {**MEDIUM, "ph": 5.0})
    assert amount(acid, "lime") == 400 and "plan.note.acid" in acid["notes"]
    assert amount(plan.build_plan("maize", {**MEDIUM, "ph": 5.8}), "lime") == 200
    assert amount(plan.build_plan("maize", MEDIUM), "lime") == 0
    alk = plan.build_plan("maize", {**MEDIUM, "ph": 8.8})
    assert "plan.note.alkaline" in alk["notes"] and amount(alk, "lime") == 0
    assert amount(plan.build_plan("maize", {**MEDIUM, "organic_matter": 0.3}), "fym") == 4000
    assert amount(plan.build_plan("maize", MEDIUM), "fym") == 2000


def test_stage_marks_passed_steps_and_shopping_skips_them():
    states = lambda stage: {s["id"]: s["state"] for s in plan.build_plan("rice", MEDIUM, stage)["steps"]}
    assert states("before") == {"prep": "now", "basal": "now", "top1": "later", "top2": "later"}
    assert states("early") == {"prep": "past", "basal": "past", "top1": "now", "top2": "later"}
    assert states("middle") == {"prep": "past", "basal": "past", "top1": "past", "top2": "now"}
    full, mid = plan.build_plan("rice", MEDIUM, "before"), plan.build_plan("rice", MEDIUM, "middle")
    assert amount(mid, "dap", states=("now", "later")) == 0 and "plan.note.past" in mid["notes"]
    assert sum(s["kg"] for s in mid["shopping"]) < sum(s["kg"] for s in full["shopping"])


def test_plantation_crops_use_rounds_not_days():
    p = plan.build_plan("coffee", MEDIUM, "middle")
    rounds = [s for s in p["steps"] if s["id"].startswith("round")]
    assert len(rounds) == 2 and all(s["state"] is None and s["day"] is None for s in rounds)
    assert "plan.note.perennial" in p["notes"]


def test_endpoint(client, other_client, field_id, use):
    use("black")
    add_test(client, field_id, nitrogen=100, phosphorus=8, potassium=60, ph=6.4)
    aid = analyze(client, field_id).json()["id"]
    r = client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "tomato", "stage": "early"})
    assert r.status_code == 200 and r.json()["available"] and r.json()["crop"] == "tomato"
    assert client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "tomato"}).json()["stage"] == "before"
    bad = client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "dragonfruit"})
    assert bad.status_code == 422 and bad.json()["message_key"] == "plan.unknown_crop"
    assert client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "rice", "stage": "x"}).status_code == 422
    assert other_client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "rice"}).status_code == 404
    assert client.get(f"{API}/fertilizer-plan/crops").json()["crops"] == plan.crop_ids()


def test_photo_only_analysis_needs_lab_values(client, field_id, use):
    use("black")
    add_photo(client, field_id)
    aid = analyze(client, field_id).json()["id"]
    r = client.get(f"{API}/analyses/{aid}/fertilizer-plan", params={"crop": "rice"})
    assert r.status_code == 200 and r.json() == {"available": False, "reason_key": "crops.need_lab"}
