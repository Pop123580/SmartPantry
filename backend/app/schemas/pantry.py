"""Pantry schemas — response keys match the frontend ``PantryItem``
TypeScript interface exactly (camelCase, ``expiresAt``/``imageUrl``)."""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import iso_z, tidy_quantity


def _to_naive_utc(value: datetime | None) -> datetime | None:
    """The DB stores naive UTC; convert any tz-aware input accordingly."""
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value

RiskLevel = Literal["low", "medium", "high"]
ItemStatus = Literal["safe", "expiring_soon", "running_low"]


class CreatePantryItemDTO(BaseModel):
    """``POST /api/pantry`` body (also the receipt-confirm DTO)."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    quantity: float = Field(gt=0, le=1_000_000)
    unit: str = Field(default="pcs", min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=80)
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024)
    storage_location: str | None = Field(
        default=None, alias="storageLocation", max_length=50
    )
    # Optional REAL price (per unit) — never required for manual entry.
    purchase_price: float | None = Field(
        default=None, alias="purchasePrice", ge=0, le=10_000_000
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("expires_at", mode="before")
    @classmethod
    def _blank_date_is_none(cls, value: object) -> object:
        return None if value in ("", None) else value

    @field_validator("expires_at")
    @classmethod
    def _naive_utc(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)


class UpdatePantryItemDTO(BaseModel):
    """``PATCH /api/pantry/{id}`` body — every field optional."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: float | None = Field(default=None, gt=0, le=1_000_000)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    category: str | None = Field(default=None, max_length=80)
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024)
    storage_location: str | None = Field(
        default=None, alias="storageLocation", max_length=50
    )
    purchase_price: float | None = Field(
        default=None, alias="purchasePrice", ge=0, le=10_000_000
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("expires_at", mode="before")
    @classmethod
    def _blank_date_is_none(cls, value: object) -> object:
        return None if value in ("", None) else value

    @field_validator("expires_at")
    @classmethod
    def _naive_utc(cls, value: datetime | None) -> datetime | None:
        return _to_naive_utc(value)


class PantryItemOut(BaseModel):
    """GET response — exactly the frontend ``PantryItem`` shape:

    ``{id, name, quantity, unit, category, status, risk, expiresAt, imageUrl}``
    """

    id: UUID
    name: str
    quantity: float
    unit: str
    category: str
    status: ItemStatus
    risk: RiskLevel
    expires_at: datetime | None = Field(alias="expiresAt")
    image_url: str | None = Field(alias="imageUrl")

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)

    @field_serializer("expires_at")
    def _exp(self, value: datetime | None) -> str | None:
        return iso_z(value)
