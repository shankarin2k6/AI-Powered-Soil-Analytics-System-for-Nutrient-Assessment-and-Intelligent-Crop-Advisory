"""Pure scoring rules (no models, no database)."""
import pytest

from app.services import soil_health as sh

GOOD = {"nitrogen": 300, "phosphorus": 30, "potassium": 150, "ph": 6.8, "organic_matter": 1.5}
POOR = {"nitrogen": 40, "phosphorus": 3, "potassium": 20, "ph": 4.6, "organic_matter": 0.3}


@pytest.mark.parametrize("name,value,level", [
    ("nitrogen", 124.9, "low"), ("nitrogen", 125, "medium"), ("nitrogen", 250, "medium"), ("nitrogen", 250.1, "high"),
    ("phosphorus", 9.9, "low"), ("potassium", 126, "high"), ("organic_matter", 0.5, "low")])
def test_nutrient_levels(name, value, level):
    assert sh.nutrient_level(name, value) == level


@pytest.mark.parametrize("ph,level", [(4.0, "strongly_acidic"), (5.7, "acidic"), (6.0, "optimal"), (7.5, "optimal"),
                                      (7.9, "alkaline"), (9.0, "strongly_alkaline")])
def test_ph_levels(ph, level):
    assert sh.ph_level(ph) == level


def test_scores_are_between_0_and_1_and_rise_with_the_value():
    for name in ("nitrogen", "phosphorus", "potassium", "organic_matter"):
        scores = [sh.nutrient_score(name, v) for v in (0, 5, 50, 100, 200, 400)]
        assert scores == sorted(scores) and 0 <= scores[0] and scores[-1] <= 1
    assert sh.ph_score(6.5) == 1.0 and sh.ph_score(4.5) == 0.0 and sh.ph_score(9.5) == 0.0
    assert sh.ph_score(7.5) > sh.ph_score(8.5) > sh.ph_score(9.2)


def test_health_score_orders_good_above_poor():
    good, poor = sh.health_score(sh.rate_lab(GOOD)), sh.health_score(sh.rate_lab(POOR))
    assert good["grade"] == "good" and good["score"] > 90
    assert poor["grade"] == "poor" and poor["score"] < 25
    assert abs(sum(c["weight"] for c in good["components"]) - 1) < 0.01


def test_health_score_reweights_when_values_are_missing():
    findings = sh.rate_lab({k: v for k, v in GOOD.items() if k != "organic_matter"})
    score = sh.health_score(findings)
    assert len(score["components"]) == 4 and abs(sum(c["weight"] for c in score["components"]) - 1) < 0.01
    assert sh.health_score([]) is None


def test_degradation_risk_follows_the_soil_condition():
    low = sh.degradation_risk(sh.rate_lab(GOOD), "Alluvial")
    high = sh.degradation_risk(sh.rate_lab(POOR), "Laterite")
    assert low["level"] == "low" and high["level"] == "high" and high["index"] > low["index"]
    assert high["drivers"] and high["drivers"][0]["share"] >= high["drivers"][-1]["share"]
    without_photo = sh.degradation_risk(sh.rate_lab(POOR), None)
    assert all(d["factor"] != "soil_type" for d in without_photo["drivers"])
    assert sh.degradation_risk([], None) is None


def test_diagnosis_lists_low_nutrients_and_ph_and_cross_checks_the_model():
    d = sh.diagnose(sh.rate_lab(POOR), ["Urea", "SSP"])
    by = {x["nutrient"]: x for x in d["deficiencies"]}
    assert set(by) == {"nitrogen", "phosphorus", "potassium", "organic_matter"}
    assert by["nitrogen"]["support"] == ["lab", "model"] and by["phosphorus"]["support"] == ["lab", "model"]
    assert by["potassium"]["support"] == ["lab"]
    assert d["ph_issue"]["level"] == "strongly_acidic" and d["summary_key"] == "diagnosis.issues_found"
    healthy = sh.diagnose(sh.rate_lab(GOOD))
    assert healthy["deficiencies"] == [] and healthy["ph_issue"] is None and healthy["summary_key"] == "diagnosis.none_found"
    assert sh.diagnose([])["summary_key"] == "diagnosis.no_lab"


def test_lab_ph_picks_the_only_fitting_candidate():
    assert sh.lab_ph_hint(7.8, ["Black", "Red"]) == "Black"
    assert sh.lab_ph_hint(6.8, ["Alluvial", "Red"]) is None      # both ranges contain 6.8: no hint
    assert sh.lab_ph_hint(None, ["Black", "Red"]) is None
    assert sh.ph_matches_soil(4.0, "Black") is False and sh.ph_matches_soil(7.5, "Black") is True
