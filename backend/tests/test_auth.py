import jwt
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas import normalize_phone
from tests.conftest import PASSWORD, make_soil_image

SIGNUP = {"name": "Lakshmi", "phone": "9876543210", "password": PASSWORD}


# ------------------------------------------------------------------ phone numbers
@pytest.mark.parametrize("raw", ["9876543210", "+91 98765 43210", "098765-43210", "919876543210", " 98765 43210 "])
def test_phone_formats_are_normalised(raw):
    assert normalize_phone(raw) == "9876543210"


@pytest.mark.parametrize("raw", ["", "12345", "5876543210", "98765432101", "abcdefghij", "+1 415 555 2671"])
def test_invalid_phone_numbers(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


# ------------------------------------------------------------------ signup
def test_signup_creates_account_and_signs_in(anonymous):
    r = anonymous.post("/api/v1/auth/signup", json={**SIGNUP, "phone": "+91 98765 43210", "language": "kn"})
    assert r.status_code == 201
    body = r.json()
    assert body["phone"] == "9876543210" and body["language"] == "kn" and body["name"] == "Lakshmi"
    assert "password" not in body and "password_hash" not in body
    assert anonymous.get("/api/v1/auth/me").json()["id"] == body["id"]      # cookie was set


def test_session_cookie_is_httponly_and_lax(anonymous):
    r = anonymous.post("/api/v1/auth/signup", json=SIGNUP)
    cookie = r.headers["set-cookie"].lower()
    assert settings.cookie_name in cookie and "httponly" in cookie and "samesite=lax" in cookie


def test_password_is_stored_hashed(anonymous):
    from app.db import get_db
    from app.models_db import Farmer
    anonymous.post("/api/v1/auth/signup", json=SIGNUP)
    stored = next(app.dependency_overrides[get_db]()).query(Farmer).one().password_hash
    assert PASSWORD not in stored and stored.startswith("$argon2")


def test_duplicate_phone_is_rejected_even_when_written_differently(anonymous):
    assert anonymous.post("/api/v1/auth/signup", json=SIGNUP).status_code == 201
    again = anonymous.post("/api/v1/auth/signup", json={**SIGNUP, "phone": "+91-98765-43210", "name": "Someone else"})
    assert again.status_code == 409


@pytest.mark.parametrize("bad", [
    {"password": "short"}, {"password": "x" * 129}, {"phone": "12345"}, {"name": "   "}, {"name": ""},
    {"language": "fr"}, {"phone": None}, {"password": None},
])
def test_signup_validation(anonymous, bad):
    assert anonymous.post("/api/v1/auth/signup", json={**SIGNUP, **bad}).status_code == 422


# ------------------------------------------------------------------ login and logout
def test_login_with_correct_password(anonymous):
    anonymous.post("/api/v1/auth/signup", json=SIGNUP)
    anonymous.post("/api/v1/auth/logout")
    assert anonymous.get("/api/v1/auth/me").status_code == 401
    r = anonymous.post("/api/v1/auth/login", json={"phone": "98765 43210", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["name"] == "Lakshmi"
    assert anonymous.get("/api/v1/auth/me").status_code == 200


def test_wrong_password_and_unknown_phone_give_the_same_answer(anonymous):
    anonymous.post("/api/v1/auth/signup", json=SIGNUP)
    anonymous.post("/api/v1/auth/logout")
    wrong = anonymous.post("/api/v1/auth/login", json={"phone": "9876543210", "password": "wrong-password"})
    unknown = anonymous.post("/api/v1/auth/login", json={"phone": "9000000000", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert anonymous.get("/api/v1/auth/me").status_code == 401         # failed login set no cookie


def test_login_requires_valid_phone_format(anonymous):
    assert anonymous.post("/api/v1/auth/login", json={"phone": "abc", "password": "x"}).status_code == 422


def test_accounts_without_password_cannot_log_in(anonymous):
    """Rows created before login existed have no password hash."""
    from app.db import get_db
    from app.models_db import Farmer
    db = next(app.dependency_overrides[get_db]())
    db.add(Farmer(name="Old", phone="9111111111", password_hash=None))
    db.commit()
    assert anonymous.post("/api/v1/auth/login", json={"phone": "9111111111", "password": "anything-at-all"}).status_code == 401


def test_logout_clears_the_session(client):
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


# ------------------------------------------------------------------ tokens
def test_bearer_header_works_without_cookie(client, anonymous):
    token = client.cookies.get(settings.cookie_name)
    assert token
    assert anonymous.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200


def test_tampered_expired_and_foreign_tokens_are_rejected(anonymous, client):
    me = client.get("/api/v1/auth/me").json()["id"]
    good = client.cookies.get(settings.cookie_name)

    def status(token):
        return anonymous.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code

    assert status(good) == 200
    assert status(good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")) == 401        # tampered
    assert status(jwt.encode({"sub": str(me), "exp": 1}, settings.secret_key, "HS256")) == 401   # expired
    assert status(jwt.encode({"sub": str(me)}, "another-secret-key-another-secret-key", "HS256")) == 401
    assert status(jwt.encode({"sub": "99999"}, settings.secret_key, "HS256")) == 401        # no such farmer
    none_token = jwt.encode({"sub": str(me)}, None, algorithm="none")
    assert status(none_token) == 401                                                         # alg=none attack
    assert status("not-a-token") == 401


# ------------------------------------------------------------------ everything is protected
PROTECTED = [
    ("get", "/api/v1/auth/me"), ("get", "/api/v1/fields"), ("post", "/api/v1/fields"),
    ("get", "/api/v1/fields/1"), ("get", "/api/v1/fields/1/images"), ("post", "/api/v1/fields/1/images"),
    ("get", "/api/v1/fields/1/soil-tests"), ("post", "/api/v1/fields/1/soil-tests"),
    ("get", "/api/v1/fields/1/history"), ("get", "/api/v1/images/1"), ("get", "/api/v1/images/1/file"),
    ("get", "/api/v1/soil-tests/1"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_endpoints_require_sign_in(anonymous, method, path):
    assert getattr(anonymous, method)(path).status_code == 401


def test_health_is_public(anonymous):
    assert anonymous.get("/health").status_code == 200


# ------------------------------------------------------------------ farmers cannot see each other's data
def test_other_farmers_data_is_invisible(client, other_client):
    field = client.post("/api/v1/fields", json={"name": "Mine"}).json()["id"]
    image = client.post(f"/api/v1/fields/{field}/images",
                        files={"file": ("s.jpg", make_soil_image(), "image/jpeg")}).json()
    test = client.post(f"/api/v1/fields/{field}/soil-tests",
                       json={"nitrogen": 1, "phosphorus": 2, "potassium": 3, "ph": 7}).json()

    attempts = [
        other_client.get(f"/api/v1/fields/{field}"),
        other_client.get(f"/api/v1/fields/{field}/images"),
        other_client.get(f"/api/v1/fields/{field}/soil-tests"),
        other_client.get(f"/api/v1/fields/{field}/history"),
        other_client.get(f"/api/v1/images/{image['id']}"),
        other_client.get(f"/api/v1/images/{image['id']}/file?variant=original"),
        other_client.get(f"/api/v1/soil-tests/{test['id']}"),
        other_client.post(f"/api/v1/fields/{field}/images", files={"file": ("s.jpg", make_soil_image(), "image/jpeg")}),
        other_client.post(f"/api/v1/fields/{field}/soil-tests", json={"nitrogen": 1, "phosphorus": 2, "potassium": 3, "ph": 7}),
    ]
    assert [r.status_code for r in attempts] == [404] * len(attempts)
    assert other_client.get("/api/v1/fields").json() == []
    assert client.get(f"/api/v1/fields/{field}/history").status_code == 200       # the owner still can


def test_each_farmer_sees_only_own_fields(client, other_client):
    client.post("/api/v1/fields", json={"name": "A"})
    other_client.post("/api/v1/fields", json={"name": "B"})
    assert [f["name"] for f in client.get("/api/v1/fields").json()] == ["A"]
    assert [f["name"] for f in other_client.get("/api/v1/fields").json()] == ["B"]


def test_soil_test_cannot_link_to_another_farmers_photo(client, other_client):
    theirs = client.post("/api/v1/fields", json={"name": "A"}).json()["id"]
    image = client.post(f"/api/v1/fields/{theirs}/images",
                        files={"file": ("s.jpg", make_soil_image(), "image/jpeg")}).json()
    mine = other_client.post("/api/v1/fields", json={"name": "B"}).json()["id"]
    r = other_client.post(f"/api/v1/fields/{mine}/soil-tests",
                          json={"nitrogen": 1, "phosphorus": 2, "potassium": 3, "ph": 7, "image_id": image["id"]})
    assert r.status_code == 422


def test_production_refuses_unsafe_settings():
    from app.config import DEV_SECRET, Settings
    safe = dict(environment="production", secret_key="x" * 48, cookie_secure=True)
    Settings(**safe).check_production_ready()                                   # fine
    for bad in ({"secret_key": DEV_SECRET}, {"secret_key": "short"}, {"cookie_secure": False}):
        with pytest.raises(RuntimeError):
            Settings(**{**safe, **bad}).check_production_ready()
    Settings(environment="development").check_production_ready()                # development is relaxed
