"""File storage behind a tiny interface (save / read / exists) with four back ends:

  local  a folder on the server (development, or a server with a persistent disk)
  s3     Amazon S3 or any S3-compatible service (set S3_ENDPOINT_URL for those)
  gcs    Google Cloud Storage
  db     the PostgreSQL database itself (for free hosts whose disk is wiped; small photos only, mind the database size)

Choose with STORAGE_BACKEND (see config.py and DEPLOYMENT.md). Nothing else in the project depends on which one is used.
The cloud libraries are imported only when used.
"""
from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


def check_key(key: str) -> str:
    """Keys look like "images/3/abc/original.jpg". Refuse anything that could climb out of the storage root."""
    if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
        raise ValueError("Invalid storage key")
    return key


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / check_key(key)).resolve()
        if self.root.resolve() not in path.parents:          # never leave the storage folder
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3Storage:
    """Amazon S3 or an S3-compatible service. `client` can be passed in for tests."""

    def __init__(self, bucket: str, prefix: str = "", client=None, region: str = "", endpoint_url: str = ""):
        if client is None:
            import boto3
            client = boto3.client("s3", region_name=region or None, endpoint_url=endpoint_url or None)
        self.client, self.bucket, self.prefix = client, bucket, prefix

    def _key(self, key: str) -> str:
        return self.prefix + check_key(key)

    @staticmethod
    def _missing(exc) -> bool:
        code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
        return code in ("NoSuchKey", "404", "NotFound")

    def save(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=data)

    def read(self, key: str) -> bytes:
        from botocore.exceptions import ClientError
        try:
            return self.client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"].read()
        except ClientError as exc:
            if self._missing(exc):
                raise FileNotFoundError(key) from exc
            raise

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError as exc:
            if self._missing(exc):
                return False
            raise                                   # for example "access denied" must not look like "no such file"


class GCSStorage:
    """Google Cloud Storage. `client` can be passed in for tests."""

    def __init__(self, bucket: str, prefix: str = "", client=None):
        if client is None:
            from google.cloud import storage as gcs
            client = gcs.Client()
        self.bucket, self.prefix = client.bucket(bucket), prefix

    def _blob(self, key: str):
        return self.bucket.blob(self.prefix + check_key(key))

    def save(self, key: str, data: bytes) -> None:
        self._blob(key).upload_from_string(data)

    def read(self, key: str) -> bytes:
        from google.api_core.exceptions import NotFound
        try:
            return self._blob(key).download_as_bytes()
        except NotFound as exc:
            raise FileNotFoundError(key) from exc

    def exists(self, key: str) -> bool:
        return self._blob(key).exists()


class DbStorage:
    """Files as rows in the `stored_files` table. Photos are resized to at most 1600 px before they get here."""

    def __init__(self, session_factory=None):
        if session_factory is None:
            from app.db import SessionLocal
            session_factory = SessionLocal
        self.session_factory = session_factory

    def save(self, key: str, data: bytes) -> None:
        from app.models_db.tables import StoredFile
        with self.session_factory() as db:
            db.merge(StoredFile(key=check_key(key), data=data))
            db.commit()

    def read(self, key: str) -> bytes:
        from app.models_db.tables import StoredFile
        with self.session_factory() as db:
            row = db.get(StoredFile, check_key(key))
            if row is None:
                raise FileNotFoundError(key)
            return bytes(row.data)

    def exists(self, key: str) -> bool:
        from app.models_db.tables import StoredFile
        with self.session_factory() as db:
            return db.get(StoredFile, check_key(key)) is not None


def make_storage() -> Storage:
    if settings.storage_backend == "db":
        return DbStorage()
    if settings.storage_backend == "s3":
        return S3Storage(settings.storage_bucket, settings.storage_prefix, region=settings.aws_region,
                         endpoint_url=settings.s3_endpoint_url)
    if settings.storage_backend == "gcs":
        return GCSStorage(settings.storage_bucket, settings.storage_prefix)
    return LocalStorage(settings.storage_dir)


_storage: Storage | None = None


def get_storage() -> Storage:
    """FastAPI dependency (tests override it with a temporary folder)."""
    global _storage
    if _storage is None:
        _storage = make_storage()
    return _storage
