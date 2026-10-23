"""Test setup: SQLite in memory and a temporary upload folder, so tests need no PostgreSQL."""
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.services.storage import LocalStorage, get_storage
from app import models_db  # noqa: F401  (registers the tables)


PASSWORD = "correct-horse-1"


@pytest.fixture()
def env(tmp_path):
    """A fresh in-memory database and a temporary upload folder for every test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    storage = LocalStorage(tmp_path / "uploads")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.clear()


@pytest.fixture()
def anonymous(env):
    """A client that is not signed in."""
    with TestClient(app) as c:
        c.storage = env
        yield c


def signed_in_client(env, phone, name="Test Farmer"):
    c = TestClient(app)
    r = c.post("/api/v1/auth/signup", json={"name": name, "phone": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    c.storage = env
    return c


@pytest.fixture()
def client(env):
    """A client signed in as farmer 9876543210."""
    with signed_in_client(env, "9876543210") as c:
        yield c


@pytest.fixture()
def other_client(env):
    """A second farmer, to check that data is not shared between accounts."""
    with signed_in_client(env, "9123456780", "Other Farmer") as c:
        yield c


@pytest.fixture()
def field_id(client):
    return client.post("/api/v1/fields", json={"name": "North plot"}).json()["id"]


def make_soil_image(size=(640, 480), fmt="JPEG", base=(150, 90, 60), exif_orientation=None) -> bytes:
    """A noisy brown picture with a darker 'soil' patch, roughly like a close-up soil photo."""
    rng = np.random.default_rng(0)
    arr = np.full((size[1], size[0], 3), base, np.float32) + rng.normal(0, 25, (size[1], size[0], 3))
    arr[size[1] // 4: 3 * size[1] // 4, size[0] // 4: 3 * size[0] // 4] *= 0.7
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        img.save(buf, fmt, exif=exif)
    else:
        img.save(buf, fmt)
    return buf.getvalue()
