from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models_db import Farmer
from app.schemas import FarmerOut, LanguageUpdate, LoginIn, ProfileUpdate, SignupIn
from app.services.auth import create_token, get_current_farmer, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _start_session(response: Response, farmer: Farmer) -> None:
    response.set_cookie(
        settings.cookie_name, create_token(farmer.id),
        max_age=settings.access_token_days * 24 * 3600,
        httponly=True,                    # JavaScript cannot read it
        samesite="lax",                   # not sent with requests started by other websites
        secure=settings.cookie_secure,    # true in production (HTTPS)
        path="/",
    )


@router.post("/signup", response_model=FarmerOut, status_code=201)
def signup(body: SignupIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(Farmer.id).where(Farmer.phone == body.phone)):
        raise HTTPException(409, "This phone number is already registered. Please log in.")
    farmer = Farmer(name=body.name, phone=body.phone, language=body.language,
                    password_hash=hash_password(body.password))
    db.add(farmer)
    try:
        db.commit()
    except IntegrityError:                # two signups at the same moment
        db.rollback()
        raise HTTPException(409, "This phone number is already registered. Please log in.")
    _start_session(response, farmer)
    return farmer


@router.post("/login", response_model=FarmerOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    farmer = db.scalar(select(Farmer).where(Farmer.phone == body.phone))
    # Same answer for "no such phone" and "wrong password"
    if not verify_password(farmer.password_hash if farmer else None, body.password):
        raise HTTPException(401, "Wrong phone number or password.")
    _start_session(response, farmer)
    return farmer


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.cookie_name, path="/")
    return {"ok": True}


@router.get("/me", response_model=FarmerOut)
def me(farmer: Farmer = Depends(get_current_farmer)):
    return farmer


@router.patch("/me", response_model=FarmerOut)
def update_me(body: ProfileUpdate, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    """Edit the signed-in farmer's own details. The login stays valid (the session is tied to the account id)."""
    taken = db.scalar(select(Farmer.id).where(Farmer.phone == body.phone, Farmer.id != farmer.id))
    if taken:
        raise HTTPException(409, "This phone number is already registered.")
    farmer.name, farmer.phone, farmer.email, farmer.address = body.name, body.phone, body.email, body.address
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This phone number is already registered.")
    return farmer


@router.put("/me/language", response_model=FarmerOut)
def set_language(body: LanguageUpdate, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    """Remember the language the farmer chose, so the app opens in it on any phone they log in from."""
    farmer.language = body.language
    db.commit()
    return farmer
