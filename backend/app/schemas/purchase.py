"""Purchase history schemas (checkout creates these; receipt flow can)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

from app.schemas.common import iso_z, tidy_quantity


class PurchaseItemOut(BaseModel):
    id: UUID
    name: str
    quantity: float
    unit: str
    unit_price: float | None = Field(alias="unitPrice")
    total_price: float | None = Field(alias="totalPrice")
    category: str | None

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)


class PurchaseOut(BaseModel):
    """Money fields are NULL when real prices were never recorded — the
    frontend must render "value unavailable" rather than an estimate."""

    id: UUID
    purchased_at: datetime = Field(alias="purchasedAt")
    total_amount: float | None = Field(alias="totalAmount")
    currency: str | None
    source: str
    receipt_url: str | None = Field(alias="receiptUrl")
    items: list[PurchaseItemOut]
    created_at: datetime = Field(alias="createdAt")

    @field_serializer("purchased_at", "created_at")
    def _ts(self, value: datetime | None) -> str | None:
        return iso_z(value)


class PurchaseSummaryOut(BaseModel):
    """List view (without nested items) for history screens."""

    id: UUID
    purchased_at: datetime = Field(alias="purchasedAt")
    total_amount: float | None = Field(alias="totalAmount")
    currency: str | None
    source: str
    item_count: int = Field(alias="itemCount")

    @field_serializer("purchased_at")
    def _ts(self, value: datetime | None) -> str | None:
        return iso_z(value)
