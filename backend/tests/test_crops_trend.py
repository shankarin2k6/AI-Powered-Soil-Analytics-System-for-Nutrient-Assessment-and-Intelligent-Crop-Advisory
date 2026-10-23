"""Milestone 3: crop suitability ranking and the soil health trend."""
from datetime import datetime, timedelta

import pytest

from app.services import crops, trend
from tests.test_analysis import add_photo, add_test, analyze, registries, use  # noqa: F401  (helpers + fixtures)

GOOD = {"nitrogen": 300, "phosphorus": 30, "potassium": 150, "ph": 6.8}
ACID = {"nitrogen": 300, "phosphorus": 30, "potassium": 150, "ph": 4.8}
POOR = {"nitrogen": 40, "phosphorus": 3, "potassium": 20, "ph": 6.8}


def ids(r):
    return [c["crop"] for c in r["top"]]


def test_ranking_follows_ph_and_soil_type():
    acid = crops.rank_crops(ACID, "Mountain")
    assert acid["available"] and ids(acid)[0] == "tea"                    # tea likes pH 4.5-5.5 on mountain soil
    assert "wheat" not in ids(acid) and "cotton" not in ids(acid)
    black = crops.rank_crops(GOOD, "Black")
    assert ids(black)[0] in {"cotton", "sugarcane", "soybean", "jowar", "wheat", "chickpea"}
    assert "tea" not in ids(black)


def test_scores_are_sorted_and_in_range():
    r = crops.rank_crops(GOOD, "Alluvial")
    scores = [c["score"] for c in r["top"]]
    assert scores == sorted(scores, reverse=True) and all(0 <= s <= 100 for s in scores) and len(scores) <= 5


def test_low_nutrients_lower_demanding_crops_more():
    good, poor = crops.rank_crops(GOOD, "Alluvial", top=30), crops.rank_crops(POOR, "Alluvial", top=30)
    score = lambda r, c: next((x["score"] for x in r["top"] if x["crop"] == c), 0)
    assert score(poor, "sugarcane") < score(good, "sugarcane")
    keys = {x["key"] for c in poor["top"] for x in c["reasons"]}
    assert "crops.reason.add_nitrogen" in keys


def test_works_without_a_soil_type_and_needs_lab_values():
    assert crops.rank_crops(GOOD, None)["available"]
    assert crops.rank_crops({"ph": 6.5}, "Red") == {"available": False, "reason_key": "crops.need_lab"}


def test_every_crop_in_the_file_is_complete():
    cfg = crops.load_crops()
    for cid, c in cfg["crops"].items():
        assert c["ph"][0] < c["ph"][1] and all(c[k] in cfg["demand_level"] for k in "npk"), cid
        assert set(c["good"]) | set(c["fair"]) <= {"Alluvial", "Arid", "Black", "Laterite", "Mountain", "Red", "Yellow"}, cid


def _row(i, day, score):
    return (i, datetime(2026, 1, 1) + timedelta(days=day), {"health": {"score": score}, "degradation": {"index": 100 - score}})


def test_trend_needs_three_points_over_two_weeks():
    assert trend.build_trend([_row(1, 0, 50), _row(2, 5, 60)])["enough_data"] is False
    assert trend.build_trend([_row(1, 0, 50), _row(2, 5, 55), _row(3, 9, 60)])["enough_data"] is False
    assert trend.build_trend([])["message_key"] == "trend.not_enough"


@pytest.mark.parametrize("scores,direction", [([50, 58, 66], "improving"), ([70, 62, 55], "declining"), ([60, 60.5, 60], "steady")])
def test_trend_direction(scores, direction):
    t = trend.build_trend([_row(i, i * 30, s) for i, s in enumerate(scores, 1)])
    assert t["enough_data"] and t["direction"] == direction and t["message_key"] == f"trend.{direction}"
    assert 0 <= t["estimate_90d"] <= 100


def test_trend_skips_photo_only_analyses():
    rows = [(9, datetime(2026, 1, 1), {"health": None}), _row(1, 0, 50)]
    assert len(trend.build_trend(rows)["points"]) == 1


def test_analysis_result_contains_crops_and_trend_endpoint_is_private(client, other_client, field_id, use):
    use("none")
    add_test(client, field_id, nitrogen=200, phosphorus=15, potassium=90, ph=6.4)
    r = analyze(client, field_id)
    assert r.status_code == 201, r.text
    c = r.json()["result"]["crops"]
    assert c["available"] and c["top"] and c["top"][0]["message_key"].startswith("crops.fit.")
    tr = client.get(f"/api/v1/fields/{field_id}/trend").json()
    assert len(tr["points"]) == 1 and tr["enough_data"] is False
    assert other_client.get(f"/api/v1/fields/{field_id}/trend").status_code == 404


def test_photo_only_analysis_has_no_crops(client, field_id, use):
    use("black")
    add_photo(client, field_id)
    r = analyze(client, field_id)
    assert r.status_code == 201 and r.json()["result"]["crops"] == {"available": False, "reason_key": "crops.need_lab"}
