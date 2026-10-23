"""Profile menu backend: edit name, phone and the optional email and address."""
import pytest

from tests.conftest import PASSWORD, signed_in_client

ME = "/api/v1/auth/me"
FULL = {"name": "Lakshmi N", "phone": "9876543210", "email": "lakshmi@example.com", "address": "12 Mill Road, Erode"}


def test_new_account_has_empty_optional_details(client):
    me = client.get(ME).json()
    assert me["email"] is None and me["address"] is None


def test_edit_all_details_and_read_them_back(client):
    r = client.patch(ME, json=FULL)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "lakshmi@example.com" and r.json()["address"] == "12 Mill Road, Erode"
    assert client.get(ME).json()["name"] == "Lakshmi N"


def test_email_and_address_are_optional_and_can_be_removed(client):
    client.patch(ME, json=FULL)
    r = client.patch(ME, json={"name": "Lakshmi N", "phone": "9876543210", "email": "", "address": "   "})
    assert r.status_code == 200 and r.json()["email"] is None and r.json()["address"] is None
    assert client.patch(ME, json={"name": "A", "phone": "9876543210"}).status_code == 200      # fields left out


def test_values_are_cleaned(client):
    r = client.patch(ME, json={"name": "  Ravi  ", "phone": "+91 98765-43210", "email": " Ravi@Example.COM ",
                               "address": "Line 1\n  Line 2"})
    assert r.json()["name"] == "Ravi" and r.json()["phone"] == "9876543210"
    assert r.json()["email"] == "ravi@example.com" and r.json()["address"] == "Line 1 Line 2"


@pytest.mark.parametrize("bad", [
    {"name": ""}, {"name": "   "}, {"phone": "12345"}, {"phone": None}, {"email": "not-an-email"}, {"email": "a@b"},
    {"email": "x" * 250 + "@a.com"}, {"address": "x" * 301},
])
def test_validation(client, bad):
    assert client.patch(ME, json={**FULL, **bad}).status_code == 422


def test_changing_the_phone_number_changes_the_login_id(anonymous, client):
    r = client.patch(ME, json={**FULL, "phone": "9123456789"})
    assert r.status_code == 200
    assert client.get(ME).status_code == 200                              # still signed in
    anonymous.cookies.clear()
    assert anonymous.post("/api/v1/auth/login", json={"phone": "9876543210", "password": PASSWORD}).status_code == 401
    assert anonymous.post("/api/v1/auth/login", json={"phone": "9123456789", "password": PASSWORD}).status_code == 200


def test_cannot_take_another_farmers_number(client, other_client):
    r = client.patch(ME, json={**FULL, "phone": "9123456780"})            # other_client's number
    assert r.status_code == 409
    assert client.get(ME).json()["phone"] == "9876543210"
    assert client.patch(ME, json=FULL).status_code == 200                 # keeping your own number is fine


def test_edits_only_touch_the_signed_in_farmer(client, other_client):
    client.patch(ME, json=FULL)
    other = other_client.get(ME).json()
    assert other["name"] == "Other Farmer" and other["email"] is None


def test_requires_login(anonymous):
    assert anonymous.patch(ME, json=FULL).status_code == 401


# ---------------------------------------------------------------- language (English, Hindi, Kannada, Tamil)
@pytest.mark.parametrize("lang", ["en", "hi", "kn", "ta"])
def test_language_can_be_saved_and_read_back(client, lang):
    r = client.put(f"{ME}/language", json={"language": lang})
    assert r.status_code == 200 and r.json()["language"] == lang
    assert client.get(ME).json()["language"] == lang


def test_unknown_language_is_rejected_and_login_required(client, anonymous):
    assert client.put(f"{ME}/language", json={"language": "fr"}).status_code == 422
    assert anonymous.put(f"{ME}/language", json={"language": "ta"}).status_code == 401


def test_signup_accepts_tamil(anonymous):
    r = anonymous.post("/api/v1/auth/signup", json={"name": "Meena", "phone": "9123456780", "password": PASSWORD, "language": "ta"})
    assert r.status_code == 201 and r.json()["language"] == "ta"
