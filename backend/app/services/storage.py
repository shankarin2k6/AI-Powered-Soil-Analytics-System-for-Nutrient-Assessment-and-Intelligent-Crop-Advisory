"""File storage behind a tiny interface.

Today images are saved in a local folder. In Milestone 3 add an S3Storage / GCSStorage class with the
same three methods and change get_storage() to return it. Nothing else in the project needs to change.
"""
from pathlib import Path
from typing import Protocol

from app.config import settings


class Storage(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
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


_storage: Storage | None = None


def get_storage() -> Storage:
    """FastAPI dependency (tests override it with a temporary folder)."""
    global _storage
    if _storage is None:
        _storage = LocalStorage(settings.storage_dir)
    return _storage
