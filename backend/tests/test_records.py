from datetime import date, timedelta

from tests.conftest import make_soil_image

TEST = {"nitrogen": 80, "phosphorus": 45, "potassium": 40, "ph": 6.5}


def test_field_flow(client):
    assert client.get("/api/v1/fields").json() == []
    field = client.post("/api/v1/fields", json={"name": "Plot 1", "area_acres": 2.5})
    assert field.status_code == 201
    me = client.get("/api/v1/auth/me").json()
    assert field.json()["farmer_id"] == me["id"]
    assert [f["name"] for f in client.get("/api/v1/fields").json()] == ["Plot 1"]
    assert client.get(f"/api/v1/fields/{field.json()['id']}").json()["area_acres"] == 2.5


def test_field_validation(client):
    assert client.post("/api/v1/fields", json={"name": ""}).status_code == 422
    assert client.post("/api/v1/fields", json={"name": "X", "area_acres": -1}).status_code == 422
    assert client.get("/api/v1/fields/999").status_code == 404


def test_create_soil_test_with_optional_values(client, field_id):
    r = client.post(f"/api/v1/fields/{field_id}/soil-tests",
                    json={**TEST, "organic_matter": 1.8, "moisture": 22, "tested_on": date.today().isoformat()})
    assert r.status_code == 201
    body = r.json()
    assert body["nitrogen"] == 80 and body["organic_matter"] == 1.8 and body["image_id"] is None
    assert client.get(f"/api/v1/soil-tests/{body['id']}").json()["ph"] == 6.5


def test_optional_fields_can_be_left_out(client, field_id):
    r = client.post(f"/api/v1/fields/{field_id}/soil-tests", json=TEST)
    assert r.status_code == 201 and r.json()["moisture"] is None


def test_out_of_range_and_missing_values_are_rejected(client, field_id):
    url = f"/api/v1/fields/{field_id}/soil-tests"
    for bad in ({"ph": 15}, {"ph": -1}, {"nitrogen": -5}, {"potassium": 501}, {"moisture": 101}, {"organic_matter": -1}):
        assert client.post(url, json={**TEST, **bad}).status_code == 422, bad
    for key in TEST:
        body = {k: v for k, v in TEST.items() if k != key}
        assert client.post(url, json=body).status_code == 422, key
    assert client.post(url, json={**TEST, "nitrogen": "lots"}).status_code == 422


def test_future_test_date_is_rejected(client, field_id):
    future = (date.today() + timedelta(days=2)).isoformat()
    assert client.post(f"/api/v1/fields/{field_id}/soil-tests", json={**TEST, "tested_on": future}).status_code == 422


def test_soil_test_can_link_to_photo_of_same_field_only(client, field_id):
    img = client.post(f"/api/v1/fields/{field_id}/images",
                      files={"file": ("s.jpg", make_soil_image(), "image/jpeg")}).json()
    ok = client.post(f"/api/v1/fields/{field_id}/soil-tests", json={**TEST, "image_id": img["id"]})
    assert ok.status_code == 201 and ok.json()["image_id"] == img["id"]

    other = client.post("/api/v1/fields", json={"name": "Other"}).json()["id"]
    assert client.post(f"/api/v1/fields/{other}/soil-tests", json={**TEST, "image_id": img["id"]}).status_code == 422
    assert client.post(f"/api/v1/fields/{field_id}/soil-tests", json={**TEST, "image_id": 999}).status_code == 422


def test_soil_test_for_unknown_field(client):
    assert client.post("/api/v1/fields/999/soil-tests", json=TEST).status_code == 404
    assert client.get("/api/v1/fields/999/soil-tests").status_code == 404
    assert client.get("/api/v1/soil-tests/999").status_code == 404


def test_history_mixes_photos_and_tests_newest_first(client, field_id):
    assert client.get(f"/api/v1/fields/{field_id}/history").json() == []
    img = client.post(f"/api/v1/fields/{field_id}/images",
                      files={"file": ("s.jpg", make_soil_image(), "image/jpeg")}).json()
    test = client.post(f"/api/v1/fields/{field_id}/soil-tests", json={**TEST, "image_id": img["id"]}).json()

    items = client.get(f"/api/v1/fields/{field_id}/history").json()
    assert [(i["type"], i["id"]) for i in items] == [("soil_test", test["id"]), ("image", img["id"])]
    assert items[1]["data"]["urls"]["normalized"].endswith("variant=normalized")
    assert client.get(f"/api/v1/fields/{field_id}/history?limit=1").json()[0]["type"] == "soil_test"
    assert client.get(f"/api/v1/fields/{field_id}/history?limit=0").status_code == 422
    assert client.get("/api/v1/fields/999/history").status_code == 404


def test_history_is_empty_for_other_fields(client, field_id):
    client.post(f"/api/v1/fields/{field_id}/soil-tests", json=TEST)
    other = client.post("/api/v1/fields", json={"name": "Other"}).json()["id"]
    assert client.get(f"/api/v1/fields/{other}/history").json() == []


def test_history_includes_analyses_once_milestone_2_writes_them(client, field_id):
    """The analyses table is empty now; this checks the history endpoint already knows how to show it."""
    from app.main import app
    from app.db import get_db
    from app.models_db import Analysis
    db = next(app.dependency_overrides[get_db]())
    db.add(Analysis(field_id=field_id, result={"tier": "confident"}, model_version="D"))
    db.commit()
    item = client.get(f"/api/v1/fields/{field_id}/history").json()[0]
    assert item["type"] == "analysis" and item["data"]["result"] == {"tier": "confident"}


def test_cors_allows_frontend_origin_with_cookies(client):
    r = client.options("/api/v1/auth/login", headers={"Origin": "http://localhost:3000",
                                                      "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert r.headers.get("access-control-allow-credentials") == "true"
    assert client.get("/health").json() == {"status": "ok"}


def test_soil_test_can_be_edited(client, field_id):
    img = client.post(f"/api/v1/fields/{field_id}/images", files={"file": ("a.png", make_soil_image(), "image/png")}).json()
    made = client.post(f"/api/v1/fields/{field_id}/soil-tests", json={**TEST, "moisture": 20, "image_id": img["id"]}).json()
    r = client.put(f"/api/v1/soil-tests/{made['id']}", json={**TEST, "nitrogen": 95, "organic_matter": 2.1})
    assert r.status_code == 200
    body = r.json()
    assert body["nitrogen"] == 95 and body["organic_matter"] == 2.1
    assert body["moisture"] is None                    # a value left out is cleared
    assert body["image_id"] == img["id"]               # the photo link is kept
    assert client.get(f"/api/v1/soil-tests/{made['id']}").json()["nitrogen"] == 95


def test_editing_a_soil_test_checks_values_and_owner(client, field_id):
    made = client.post(f"/api/v1/fields/{field_id}/soil-tests", json=TEST).json()
    assert client.put(f"/api/v1/soil-tests/{made['id']}", json={**TEST, "ph": 15}).status_code == 422
    assert client.put(f"/api/v1/soil-tests/{made['id']}", json={"ph": 6}).status_code == 422
    assert client.put("/api/v1/soil-tests/9999", json=TEST).status_code == 404
