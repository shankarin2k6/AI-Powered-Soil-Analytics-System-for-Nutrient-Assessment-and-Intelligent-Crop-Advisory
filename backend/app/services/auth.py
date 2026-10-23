"""Passwords, session tokens and the 'who is signed in' dependency.

How a login works: the API checks the password, then sets an httpOnly cookie holding a signed token
(JWT) with the farmer's id. The browser sends the cookie automatically on every request, including
<img> requests, and JavaScript on the page cannot read it. API clients may send the same token as
"Authorization: Bearer <token>" instead.
"""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models_db import Farmer

_hasher = PasswordHasher()
# A real hash of a throw-away password. Used when the phone number is unknown so that the time taken
# does not reveal whether an account exists.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def create_token(farmer_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(days=settings.access_token_days)
    return jwt.encode({"sub": str(farmer_id), "exp": expires}, settings.secret_key, algorithm="HS256")


def read_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def _token_from_request(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(settings.cookie_name)


def get_current_farmer(request: Request, db: Session = Depends(get_db)) -> Farmer:
    """Dependency for every protected endpoint."""
    token = _token_from_request(request)
    farmer_id = read_token(token) if token else None
    farmer = db.get(Farmer, farmer_id) if farmer_id else None
    if farmer is None:
        raise HTTPException(401, "Please sign in.", headers={"WWW-Authenticate": "Bearer"})
    return farmer
