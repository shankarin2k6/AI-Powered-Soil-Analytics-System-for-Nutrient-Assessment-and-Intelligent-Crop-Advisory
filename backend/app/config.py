"""All settings in one place. Values come from environment variables or backend/.env."""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-secret-change-me-before-deploying"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (PostgreSQL in development and production; tests use SQLite)
    database_url: str = "postgresql+psycopg://soil:soil@localhost:5432/soil"

    # Where uploaded images (and cached voice audio) are kept: STORAGE_BACKEND=local (a folder), s3, gcs or db (inside the PostgreSQL database).
    # For s3/gcs set STORAGE_BUCKET. S3 also works with S3-compatible services (set S3_ENDPOINT_URL).
    # Cloud credentials come from the usual places (AWS_ACCESS_KEY_ID / role, GOOGLE_APPLICATION_CREDENTIALS) - see DEPLOYMENT.md.
    storage_backend: str = "local"
    storage_dir: Path = Path("uploads")          # local backend only
    storage_bucket: str = ""
    storage_prefix: str = ""                      # optional folder inside the bucket, e.g. "soil/"
    s3_endpoint_url: str = ""
    aws_region: str = ""

    # Login sessions. In production set ENVIRONMENT=production, a long random SECRET_KEY
    # (python -c "import secrets; print(secrets.token_urlsafe(48))") and COOKIE_SECURE=true (needs HTTPS).
    environment: str = "development"
    secret_key: str = DEV_SECRET
    access_token_days: int = 7
    cookie_name: str = "soil_session"
    cookie_secure: bool = False

    # Comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:3000"

    # Trained models (Milestone 2). Put the files from the training notebooks in this folder.
    model_dir: Path = Path("models")
    cnn_file: str = "soil_cnn_D_hard_negatives.pt"   # 8 classes: 7 soils + Not_Soil

    # Voice (Milestone 3): Sarvam AI text-to-speech. Leave the key empty to switch the Listen button off.
    # Get a key at https://dashboard.sarvam.ai (see MILESTONE3_VOICE.md).
    sarvam_api_key: str = ""
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_model: str = "bulbul:v3"
    sarvam_speaker: str = "shubh"
    voice_max_chars: int = 2500          # Sarvam's limit per request for bulbul:v3

    # Image upload rules
    max_upload_bytes: int = 10 * 1024 * 1024   # 10 MB
    min_side_px: int = 64                      # shorter side must be at least this
    max_pixels: int = 40_000_000               # guards against decompression bombs
    normalized_max_side: int = 1600            # longest side after resizing

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, v: str) -> str:
        """Neon, Render and others give postgres://... or postgresql://...; this app uses the psycopg 3 driver."""
        for old in ("postgres://", "postgresql://"):
            if v.startswith(old):
                return "postgresql+psycopg://" + v[len(old):]
        return v

    def check_production_ready(self) -> None:
        """Stop the server from starting in production with an unsafe configuration."""
        if self.storage_backend not in ("local", "s3", "gcs", "db"):
            raise RuntimeError("STORAGE_BACKEND must be local, s3, gcs or db.")
        if self.storage_backend in ("s3", "gcs") and not self.storage_bucket:
            raise RuntimeError("Set STORAGE_BUCKET when STORAGE_BACKEND is s3 or gcs.")
        if self.environment == "production":
            if self.secret_key == DEV_SECRET or len(self.secret_key) < 32:
                raise RuntimeError("Set a long random SECRET_KEY before running in production.")
            if not self.cookie_secure:
                raise RuntimeError("Set COOKIE_SECURE=true in production (the site must use HTTPS).")

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
