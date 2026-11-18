"""Milestone 3: cloud storage back ends, production safety checks and the health endpoint.

S3 is tested against moto (a pretend S3 inside the test), Google Cloud Storage with a small fake client.
"""
import boto3
import pytest
from moto import mock_aws

from app.config import Settings
from app.services import storage as st

KEY = "images/3/abc/original.jpg"


@pytest.fixture()
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="soil-test")
        yield client


def test_s3_round_trip_prefix_and_missing(s3):
    store = st.S3Storage("soil-test", prefix="soil/", client=s3)
    assert not store.exists(KEY)
    store.save(KEY, b"photo-bytes")
    assert store.exists(KEY) and store.read(KEY) == b"photo-bytes"
    assert s3.get_object(Bucket="soil-test", Key="soil/" + KEY)["Body"].read() == b"photo-bytes"    # the prefix is applied
    with pytest.raises(FileNotFoundError):
        store.read("images/3/none.jpg")


def test_s3_errors_other_than_missing_are_not_hidden(s3):
    store = st.S3Storage("no-such-bucket", client=s3)
    with pytest.raises(Exception) as e:
        store.exists(KEY)                     # a missing bucket is a configuration problem, not "file not found"
    assert not isinstance(e.value, FileNotFoundError)


@pytest.mark.parametrize("bad", ["", "/etc/passwd", "../secret", "a/../../b", "a\\b"])
def test_keys_cannot_climb_out(s3, bad, tmp_path):
    for store in (st.S3Storage("soil-test", client=s3), st.LocalStorage(tmp_path)):
        with pytest.raises(ValueError):
            store.save(bad, b"x")


class FakeBlob:
    def __init__(self, bucket, name): self.bucket, self.name = bucket, name
    def upload_from_string(self, data): self.bucket.items[self.name] = data
    def exists(self): return self.name in self.bucket.items
    def download_as_bytes(self):
        from google.api_core.exceptions import NotFound
        if self.name not in self.bucket.items:
            raise NotFound("missing")
        return self.bucket.items[self.name]


class FakeBucket:
    def __init__(self): self.items = {}
    def blob(self, name): return FakeBlob(self, name)


class FakeGcs:
    def __init__(self): self.buckets = {}
    def bucket(self, name): return self.buckets.setdefault(name, FakeBucket())


def test_gcs_round_trip_prefix_and_missing():
    client = FakeGcs()
    store = st.GCSStorage("b", prefix="soil/", client=client)
    assert not store.exists(KEY)
    store.save(KEY, b"abc")
    assert store.exists(KEY) and store.read(KEY) == b"abc" and "soil/" + KEY in client.buckets["b"].items
    with pytest.raises(FileNotFoundError):
        store.read("nope.png")


def test_backend_is_chosen_from_settings(monkeypatch, tmp_path, s3):
    s = st.settings
    monkeypatch.setattr(s, "storage_dir", tmp_path)
    monkeypatch.setattr(s, "storage_backend", "local")
    assert isinstance(st.make_storage(), st.LocalStorage)
    monkeypatch.setattr(s, "storage_backend", "s3"); monkeypatch.setattr(s, "storage_bucket", "soil-test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    made = st.make_storage()
    assert isinstance(made, st.S3Storage) and made.bucket == "soil-test"


def prod(**kw):
    base = dict(environment="production", secret_key="x" * 40, cookie_secure=True)
    return Settings(_env_file=None, **{**base, **kw})


def test_production_checks():
    prod().check_production_ready()                                            # local storage is allowed on a persistent disk
    prod(storage_backend="s3", storage_bucket="b").check_production_ready()
    with pytest.raises(RuntimeError, match="STORAGE_BUCKET"):
        prod(storage_backend="s3").check_production_ready()
    with pytest.raises(RuntimeError, match="STORAGE_BACKEND"):
        prod(storage_backend="ftp").check_production_ready()
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        prod(secret_key="short").check_production_ready()
    with pytest.raises(RuntimeError, match="COOKIE_SECURE"):
        prod(cookie_secure=False).check_production_ready()


def test_health_endpoints(anonymous):
    assert anonymous.get("/health").json() == {"status": "ok"}
    r = anonymous.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "database": "ok"}


def test_db_storage_round_trip(db_session_factory=None):
    """STORAGE_BACKEND=db keeps files in the database."""
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.db import Base
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    store = st.DbStorage(sessionmaker(bind=engine, expire_on_commit=False))
    assert not store.exists("images/1/a.jpg")
    store.save("images/1/a.jpg", b"abc")
    store.save("images/1/a.jpg", b"abcd")            # saving again replaces
    assert store.exists("images/1/a.jpg") and store.read("images/1/a.jpg") == b"abcd"
    with pytest.raises(FileNotFoundError):
        store.read("images/1/none.jpg")
    with pytest.raises(ValueError):
        store.save("../x", b"1")
