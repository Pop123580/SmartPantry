"""Application configuration.

All values are sourced from environment variables / a local .env file.
SECURITY: there is NO default JWT secret — the application refuses to
start without ``JWT_SECRET_KEY``, and enforces a strong key in
staging/production. Nothing sensitive is hard-coded here.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_SECRET_LENGTH_PRODUCTION = 32


class Settings(BaseSettings):
    """Environment-driven settings (pydantic-settings)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Runtime environment ──────────────────────────────────────────
    environment: Literal["development", "test", "staging", "production"] = "development"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/smartpantry"
    )

    # ── Auth / JWT ───────────────────────────────────────────────────
    # NO default. ``JWT_SECRET`` remains readable (deprecated alias) so
    # older local .env files keep working, but JWT_SECRET_KEY is the
    # documented contract. Missing → the app refuses to start (below).
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
  # ── Google Authentication ──────────────────────────────────────
    google_client_id: str | None = None

    # ── AWS ──────────────────────────────────────────────────────────
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str | None = "ap-south-1"
    aws_s3_bucket: str | None = None
    bedrock_model_id: str | None = None

    # ── CORS ─────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Uploads / money ──────────────────────────────────────────────
    max_upload_size_mb: int = 5
    default_currency: str = "INR"

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def _blank_secret_is_none(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return value

    @field_validator(
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_region",
        "aws_s3_bucket",
        "bedrock_model_id",
        mode="before",
    )
    @classmethod
    def _empty_string_becomes_none(cls, value: object) -> object:
        """Treat blank env values (e.g. ``AWS_S3_BUCKET=``) as unset."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("default_currency")
    @classmethod
    def _normalise_currency(cls, value: str) -> str:
        return value.strip().upper()[:3] or "INR"

    @model_validator(mode="after")
    def _require_secure_jwt_secret(self) -> "Settings":
        secret = (
            self.jwt_secret_key.get_secret_value()
            if self.jwt_secret_key is not None
            else None
        )
        if not secret or not secret.strip():
            raise ValueError(
                "JWT_SECRET_KEY is not set. SmartPantry refuses to start "
                "with an insecure or default secret. Generate one with "
                "`openssl rand -hex 32` and set it in backend/.env "
                "(see .env.example)."
            )
        if (
            self.environment in ("staging", "production")
            and len(secret) < MIN_SECRET_LENGTH_PRODUCTION
        ):
            raise ValueError(
                f"JWT_SECRET_KEY is too short for {self.environment} "
                f"(minimum {MIN_SECRET_LENGTH_PRODUCTION} characters). "
                "Generate one with `openssl rand -hex 32`."
            )
        return self

    @property
    def jwt_secret(self) -> str:
        """Decoded secret. Never logged, never returned by the API."""
        assert self.jwt_secret_key is not None  # guaranteed by validator
        return self.jwt_secret_key.get_secret_value()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins: the configured frontend + Vite dev default."""
        origins = {self.frontend_url.rstrip("/"), "http://localhost:5173"}
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
