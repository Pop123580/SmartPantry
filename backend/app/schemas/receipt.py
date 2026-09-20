"""Receipt OCR result — a list of ``CreatePantryItemDTO``-shaped items the
frontend shows for confirmation. Nothing is inserted into the pantry."""

from pydantic import BaseModel, Field, field_serializer

from app.schemas.common import tidy_quantity


class ReceiptItemOut(BaseModel):
    """``CreatePantryItemDTO``-shaped confirmation row.

    ``unitPrice`` is present ONLY when Textract/Bedrock actually read a
    price off the receipt — otherwise ``null`` (never estimated)."""

    name: str
    quantity: float
    unit: str
    category: str
    expires_at: None = Field(default=None, alias="expiresAt")
    image_url: None = Field(default=None, alias="imageUrl")
    unit_price: float | None = Field(default=None, alias="unitPrice")
    currency: str | None = None

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)
