"""Milestone 2: the /analyze endpoint, run with stand-in models (see tests/standins.py)."""
import pytest

pytest.importorskip("torch")
pytest.importorskip("xgboost")

from app.main import app  # noqa: E402
from app.ml.loader import get_registry  # noqa: E402
from tests.conftest import make_soil_image  # noqa: E402
from tests.standins import make_registry  # noqa: E402

API = "/api/v1"
LAB = {"nitrogen": 90, "phosphorus": 8, "potassium": 140, "ph": 7.8, "organic_matter": 0.6, "moisture": 22}
CROP = {"crop_type": "Wheat", "growth_stage": "Vegetative", "season": "Rabi"}


@pytest.fixture(scope="module")
def registries():
    return {"black": make_registry({"Black": 5.0}),            # confident Black
            "confirm": make_registry({"Black": 3.3, "Red": 3.3}),   # about 45 % each: ask the farmer
            "notsoil": make_registry({"Not_Soil": 5.0}),
            "retake": make_registry({"Not_Soil": -1.0}),            # soil classes about 14 % each
            "none": make_registry(image=False, fert=False)}


@pytest.fixture()
def use(registries):
    def _use(name):
        app.dependency_overrides[get_registry] = lambda: registries[name]
    return _use


def add_photo(client, field_id):
    r = client.post(f"{API}/fields/{field_id}/images", files={"file": ("s.jpg", make_soil_image(), "image/jpeg")})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_test(client, field_id, **extra):
    r = client.post(f"{API}/fields/{field_id}/soil-tests", json={**LAB, **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def analyze(client, field_id, **body):
    return client.post(f"{API}/fields/{field_id}/analyze", json=body)


def test_nothing_to_analyze(client, field_id, use):
    use("black")
    r = analyze(client, field_id)
    assert r.status_code == 422 and r.json()["message_key"] == "analysis.nothing_to_analyze"


def test_lab_only_works_without_any_model_files(client, field_id, use):
    use("none")
    add_test(client, field_id)
    r = analyze(client, field_id)
    assert r.status_code == 201, r.text
    res = r.json()["result"]
    assert res["image"] == {"available": False, "reason_key": "analysis.no_photo"}
    assert res["fertilizer_signal"]["reason_key"] == "analysis.models_unavailable"
    assert 0 <= res["health"]["score"] <= 100 and res["degradation"]["level"] in ("low", "moderate", "high")
    assert {d["nutrient"] for d in res["diagnosis"]["deficiencies"]} == {"nitrogen", "phosphorus", "organic_matter"}
    assert all(d["support"] == ["lab"] for d in res["diagnosis"]["deficiencies"])


def test_photo_only_reports_missing_models_without_failing(client, field_id, use):
    use("none")
    add_photo(client, field_id)
    res = analyze(client, field_id).json()["result"]
    assert res["image"]["reason_key"] == "analysis.models_unavailable" and res["health"] is None
    assert res["diagnosis"]["summary_key"] == "diagnosis.no_lab"


def test_confident_photo_plus_lab_is_fused_and_saved(client, field_id, use):
    use("black")
    image_id = add_photo(client, field_id)
    test_id = add_test(client, field_id, image_id=image_id)
    r = analyze(client, field_id)
    assert r.status_code == 201, r.text
    body = r.json()
    res = body["result"]
    assert body["image_id"] == image_id and body["soil_test_id"] == test_id and body["model_version"]
    assert res["image"]["tier"] == "confident" and res["image"]["soil_class"] == "Black"
    assert res["image"]["candidates"][0]["soil_class"] == "Black" and res["image"]["has_gradcam"]
    assert res["fusion"] == {"soil_class": "Black", "soil_class_source": "image", "notes": []}   # pH 7.8 fits Black
    assert any(d["factor"] == "soil_type" for d in res["degradation"]["drivers"]) or res["degradation"]["index"] > 0
    png = client.get(f"{API}/analyses/{body['id']}/gradcam")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png" and png.content[:4] == b"\x89PNG"
    assert client.get(f"{API}/analyses/{body['id']}").json()["result"] == res
    assert [a["id"] for a in client.get(f"{API}/fields/{field_id}/analyses").json()] == [body["id"]]


def test_photo_and_lab_that_disagree_are_flagged(client, field_id, use):
    use("black")
    photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=photo, ph=4.6)                          # Black soil is never this acidic
    assert "fusion.ph_soil_mismatch" in analyze(client, field_id).json()["result"]["fusion"]["notes"]


def test_unsure_photo_asks_to_confirm_and_lab_ph_breaks_the_tie(client, field_id, use):
    use("confirm")
    photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=photo)                  # pH 7.8: Black fits, Red does not
    res = analyze(client, field_id).json()["result"]
    assert res["image"]["tier"] == "confirm"
    assert {c["soil_class"] for c in res["image"]["candidates"]} == {"Black", "Red"}
    assert res["fusion"]["soil_class"] is None and res["fusion"]["lab_hint"] == "Black"
    assert "fusion.please_confirm_soil" in res["fusion"]["notes"]
    again = analyze(client, field_id, confirmed_soil_class="Red").json()["result"]
    assert again["fusion"]["soil_class"] == "Red" and again["fusion"]["soil_class_source"] == "user"


def test_not_soil_and_retake_never_pick_a_soil_class(client, field_id, use):
    add_photo(client, field_id)
    for name, tier, gradcam in (("notsoil", "not_soil", False), ("retake", "retake", True)):
        use(name)
        body = analyze(client, field_id).json()
        res = body["result"]
        assert res["image"]["tier"] == tier and res["image"]["soil_class"] is None
        assert res["fusion"]["soil_class"] is None
        assert all(c["soil_class"] != "Not_Soil" for c in res["image"]["candidates"])
        assert res["image"].get("has_gradcam", False) is gradcam
        if not gradcam:
            assert client.get(f"{API}/analyses/{body['id']}/gradcam").status_code == 404


def test_fertilizer_signal_with_shap_explanation(client, field_id, use):
    use("black")
    photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=photo)
    res = analyze(client, field_id, **CROP).json()["result"]
    fert = res["fertilizer_signal"]
    assert fert["available"] and len(fert["recommendations"]) == 3
    assert sum(r["probability"] for r in fert["recommendations"]) <= 1.001
    assert fert["inputs_used"]["soil_type"] == "Clay"           # Black soil -> Clay
    exp = fert["explanation"]
    assert exp["method"] == "treeshap" and exp["for"] == fert["recommendations"][0]["label"]
    assert 1 <= len(exp["features"]) <= 5 and all("Crop_Type_" not in f["feature"] for f in exp["features"])
    mags = [abs(f["contribution"]) for f in exp["features"]]
    assert mags == sorted(mags, reverse=True)
    supplied = {n for r in fert["recommendations"]
                for n in {"Urea": ["nitrogen"], "DAP": ["nitrogen", "phosphorus"], "MOP": ["potassium"],
                          "SSP": ["phosphorus"], "NPK": ["nitrogen", "phosphorus", "potassium"]}.get(r["label"], [])}
    for d in res["diagnosis"]["deficiencies"]:                  # 'model' support = the top-3 fertilizers supply it
        assert ("model" in d["support"]) == (d["nutrient"] in supplied)


def test_fertilizer_part_is_skipped_without_crop_details(client, field_id, use):
    use("black")
    add_test(client, field_id)
    fert = analyze(client, field_id, crop_type="Wheat").json()["result"]["fertilizer_signal"]
    assert fert["available"] is False and fert["missing"] == ["growth_stage", "season"]


def test_unknown_crop_is_a_clear_422(client, field_id, use):
    use("black")
    add_test(client, field_id)
    r = analyze(client, field_id, **{**CROP, "crop_type": "Dragonfruit"})
    assert r.status_code == 422 and r.json()["message_key"] == "input.invalid_value"


def test_rejects_unknown_soil_class_and_foreign_ids(client, other_client, field_id, use):
    use("black")
    add_test(client, field_id)
    assert analyze(client, field_id, confirmed_soil_class="Chocolate").json()["message_key"] == "analysis.bad_soil_class"
    other_field = other_client.post(f"{API}/fields", json={"name": "Theirs"}).json()["id"]
    foreign = add_photo(other_client, other_field)
    r = analyze(client, field_id, image_id=foreign)
    assert r.status_code == 422 and r.json()["message_key"] == "analysis.bad_image"
    assert analyze(client, field_id, soil_test_id=99999).json()["message_key"] == "analysis.bad_test"


def test_explicit_photo_uses_the_test_saved_with_it(client, field_id, use):
    use("none")
    photo = add_photo(client, field_id)
    linked = add_test(client, field_id, image_id=photo, nitrogen=300)
    add_test(client, field_id)                                  # newer, but not linked
    body = analyze(client, field_id, image_id=photo).json()
    assert body["soil_test_id"] == linked


def test_new_photo_without_lab_values_never_reuses_old_values(client, field_id, use):
    use("black")
    old_photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=old_photo)              # lab values of the OLD sample
    new_photo = add_photo(client, field_id)                     # newer photo, no lab values
    body = analyze(client, field_id).json()
    assert body["image_id"] == new_photo and body["soil_test_id"] is None
    res = body["result"]
    assert res["lab"] is None and res["health"] is None and res["degradation"] is None
    assert res["diagnosis"]["summary_key"] == "diagnosis.no_lab"
    assert res["fertilizer_signal"]["reason_key"] == "analysis.no_lab"
    assert analyze(client, field_id, image_id=old_photo).json()["result"]["health"] is not None


def test_newest_lab_test_brings_its_own_photo(client, field_id, use):
    use("black")
    photo = add_photo(client, field_id)
    test = add_test(client, field_id, image_id=photo)
    body = analyze(client, field_id).json()
    assert (body["image_id"], body["soil_test_id"]) == (photo, test)
    standalone = add_test(client, field_id)                     # a later test with no photo
    body = analyze(client, field_id).json()
    assert body["image_id"] is None and body["soil_test_id"] == standalone


def test_class_names_with_soil_suffix_are_shortened(client, field_id, use, registries):
    from tests import standins
    reg = standins.make_registry({"Black": 5.0})
    reg.classes = [c if c == "Not_Soil" else f"{c}_Soil" for c in reg.classes]
    app.dependency_overrides[get_registry] = lambda: reg
    photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=photo)
    res = analyze(client, field_id).json()["result"]
    assert res["image"]["soil_class"] == "Black" and res["fusion"]["soil_class"] == "Black"
    assert all(c["soil_class"] in ("Black", "Not_Soil") or "_" not in c["soil_class"] for c in res["image"]["top3"])
    assert any(d["factor"] == "soil_type" for d in res["degradation"]["drivers"]) or res["degradation"]["index"] > 0
    assert analyze(client, field_id, confirmed_soil_class="Red").status_code == 201


def test_other_farmers_cannot_see_or_analyse(client, other_client, field_id, use):
    use("black")
    photo = add_photo(client, field_id)
    add_test(client, field_id, image_id=photo)
    aid = analyze(client, field_id).json()["id"]
    assert other_client.get(f"{API}/analyses/{aid}").status_code == 404
    assert other_client.get(f"{API}/analyses/{aid}/gradcam").status_code == 404
    assert other_client.get(f"{API}/fields/{field_id}/analyses").status_code == 404
    assert other_client.post(f"{API}/fields/{field_id}/analyze", json={}).status_code == 404


def test_requires_login(anonymous, use):
    use("black")
    assert anonymous.post(f"{API}/fields/1/analyze", json={}).status_code == 401
    assert anonymous.get(f"{API}/analyses/1").status_code == 401


def test_analysis_appears_in_history(client, field_id, use):
    use("black")
    add_test(client, field_id)
    aid = analyze(client, field_id).json()["id"]
    items = client.get(f"{API}/fields/{field_id}/history").json()
    mine = [i for i in items if i["type"] == "analysis"]
    assert [i["id"] for i in mine] == [aid] and mine[0]["data"]["result"]["health"]["score"] > 0


def test_status_endpoint(client, use):
    use("black")
    body = client.get(f"{API}/analysis/status").json()
    assert body["image_model"] and body["fertilizer_model"] and "Not_Soil" in body["classes"]
    assert body["fertilizer_options"]["crop_type"] == ["Maize", "Wheat"]
    assert body["fertilizer_options"]["season"] == ["Kharif", "Rabi"]
    use("none")
    assert client.get(f"{API}/analysis/status").json()["fertilizer_options"] == {}
