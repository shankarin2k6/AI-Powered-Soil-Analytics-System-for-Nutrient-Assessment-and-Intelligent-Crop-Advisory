"""Request and response shapes (Pydantic). They are the API contract the frontend builds against."""
import re
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- accounts
def normalize_phone(value: str) -> str:
    """'+91 98765-43210', '098765 43210' and '9876543210' all become '9876543210'."""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not (len(digits) == 10 and digits[0] in "6789"):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return digits


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str
    password: str = Field(min_length=8, max_length=128)
    language: Literal["en", "hi", "kn", "ta"] = "en"

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        return normalize_phone(v)


class LoginIn(BaseModel):
    phone: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        return normalize_phone(v)


class FarmerOut(ORM):
    id: int
    name: str
    phone: Optional[str]
    email: Optional[str] = None
    address: Optional[str] = None
    language: str
    created_at: datetime


class LanguageUpdate(BaseModel):
    """The language the farmer picked in the app: English, Hindi, Kannada or Tamil."""
    language: Literal["en", "hi", "kn", "ta"]


_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ProfileUpdate(BaseModel):
    """Edit profile form. Name and phone are required; email and address are optional (empty = remove)."""
    name: str = Field(min_length=1, max_length=120)
    phone: str
    email: Optional[str] = Field(None, max_length=254)
    address: Optional[str] = Field(None, max_length=300)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: Optional[str]) -> Optional[str]:
        v = (v or "").strip().lower()
        if not v:
            return None
        if not _EMAIL.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("address")
    @classmethod
    def clean_address(cls, v: Optional[str]) -> Optional[str]:
        v = " ".join((v or "").split())          # collapse stray line breaks and spaces
        return v or None


# ---------------------------------------------------------------- fields
class FieldCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: Optional[str] = Field(None, max_length=200)
    area_acres: Optional[float] = Field(None, gt=0, le=100000)


class FieldOut(ORM):
    id: int
    farmer_id: int
    name: str
    location: Optional[str]
    area_acres: Optional[float]
    created_at: datetime


# ---------------------------------------------------------------- images
class ImageOut(BaseModel):
    id: int
    field_id: int
    width: int
    height: int
    size_bytes: int
    content_type: str
    quality: dict[str, Any]                 # blur_score, brightness, warnings: ["image.blurry", ...]
    urls: dict[str, str]                    # original / normalized / corrected / foreground (if available)
    created_at: datetime


# ---------------------------------------------------------------- lab soil tests
class SoilTestCreate(BaseModel):
    nitrogen: float = Field(ge=0, le=500, description="mg/kg")
    phosphorus: float = Field(ge=0, le=500, description="mg/kg")
    potassium: float = Field(ge=0, le=500, description="mg/kg")
    ph: float = Field(ge=0, le=14)
    organic_matter: Optional[float] = Field(None, ge=0, le=100, description="percent")
    moisture: Optional[float] = Field(None, ge=0, le=100, description="percent")
    tested_on: Optional[date] = None
    image_id: Optional[int] = None          # the photo of the same sample, if there is one

    @field_validator("tested_on")
    @classmethod
    def not_in_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("tested_on cannot be in the future")
        return v


class SoilTestUpdate(BaseModel):
    """Replaces the values of a saved lab test. The linked photo stays as it is."""
    nitrogen: float = Field(ge=0, le=500, description="mg/kg")
    phosphorus: float = Field(ge=0, le=500, description="mg/kg")
    potassium: float = Field(ge=0, le=500, description="mg/kg")
    ph: float = Field(ge=0, le=14)
    organic_matter: Optional[float] = Field(None, ge=0, le=100, description="percent")
    moisture: Optional[float] = Field(None, ge=0, le=100, description="percent")
    tested_on: Optional[date] = None

    @field_validator("tested_on")
    @classmethod
    def not_in_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v > date.today():
            raise ValueError("tested_on cannot be in the future")
        return v


class SoilTestOut(ORM):
    id: int
    field_id: int
    image_id: Optional[int]
    nitrogen: float
    phosphorus: float
    potassium: float
    ph: float
    organic_matter: Optional[float]
    moisture: Optional[float]
    tested_on: Optional[date]
    created_at: datetime


# ---------------------------------------------------------------- history
class HistoryItem(BaseModel):
    type: Literal["image", "soil_test", "analysis"]
    id: int
    created_at: datetime
    data: dict[str, Any]


# ---------------------------------------------------------------- analysis (Milestone 2)
class AnalyzeIn(BaseModel):
    """Everything is optional: with an empty body the newest photo and the newest lab test are analysed."""
    image_id: Optional[int] = None
    soil_test_id: Optional[int] = None
    confirmed_soil_class: Optional[str] = Field(None, description="The soil type the farmer picked from the two candidates")
    # only used for the fertilizer model; without them that part is skipped
    crop_type: Optional[str] = Field(None, max_length=60)
    growth_stage: Optional[str] = Field(None, max_length=60)
    season: Optional[str] = Field(None, max_length=60)


class AnalysisOut(BaseModel):
    id: int
    field_id: int
    image_id: Optional[int]
    soil_test_id: Optional[int]
    model_version: Optional[str]
    created_at: datetime
    result: dict[str, Any]
