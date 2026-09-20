"""Shopping schemas — ``inInventory``/``imageUrl`` camelCase as the
frontend ``ShoppingItem`` interface requires."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.common import tidy_quantity
from app.schemas.pantry import PantryItemOut


class CreateShoppingItemDTO(BaseModel):
    """``POST /api/shopping`` body. ``inInventory`` is server-computed.

    ``unitPrice``/``currency`` are optional: when the user knows the real
    price it flows into the purchase record at checkout; otherwise money
    stays NULL everywhere (never estimated)."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(default=1, gt=0, le=1_000_000)
    unit: str = Field(default="pcs", min_length=1, max_length=20)
    reason: str | None = Field(default=None, max_length=300)
    image_url: str | None = Field(default=None, alias="imageUrl", max_length=1024)
    unit_price: float | None = Field(
        default=None, alias="unitPrice", ge=0, le=10_000_000
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ShoppingItemOut(BaseModel):
    """``{id, name, quantity, unit, reason, inInventory, imageUrl}`` plus
    optional real price fields (additive — always present, null when
    unknown, so older frontend types remain valid)."""

    id: UUID
    name: str
    quantity: float
    unit: str
    reason: str | None = None
    in_inventory: bool = Field(alias="inInventory")
    image_url: str | None = Field(alias="imageUrl")
    unit_price: float | None = Field(default=None, alias="unitPrice")
    currency: str | None = None

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)


class CheckoutResult(BaseModel):
    """Response of ``POST /api/shopping/checkout``."""

    purchase_id: UUID = Field(alias="purchaseId")
    cleared_items: int = Field(alias="clearedItems")
    pantry: list[PantryItemOut]
    message: str
