"""Analytics summary — built ONLY from real database rows.

Money semantics (§6 of the review spec):
* ``atRiskKnownValue``  — Σ(quantity × purchase_price) over at-risk items
  that HAVE a recorded real price. ``null`` when nothing is priced.
* ``atRiskValueUnavailableCount`` — at-risk items WITHOUT price data; the
  UI should say e.g. "3 items at risk — value unavailable" instead of
  inventing rupees.
* ``totalPurchaseValue`` — Σ purchase totals where prices were recorded.
* ``knownValueSaved`` — value of consumed stock, computable only when the
  consumed pantry item carried a real price; otherwise ``null``.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer

from app.schemas.common import iso_z, tidy_quantity


class ConsumptionEventOut(BaseModel):
    food_name: str | None = Field(alias="name")
    quantity: float
    unit: str
    consumed_at: datetime = Field(alias="consumedAt")
    recipe_id: UUID | None = Field(default=None, alias="recipeId")

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)

    @field_serializer("consumed_at")
    def _ts(self, value: datetime | None) -> str | None:
        return iso_z(value)


class WasteEventOut(BaseModel):
    food_name: str | None = Field(alias="name")
    quantity: float
    unit: str
    reason: str
    estimated_value: float | None = Field(alias="estimatedValue")
    created_at: datetime = Field(alias="createdAt")

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)

    @field_serializer("created_at")
    def _ts(self, value: datetime | None) -> str | None:
        return iso_z(value)


class RecentPurchaseOut(BaseModel):
    id: UUID
    purchased_at: datetime = Field(alias="purchasedAt")
    total_amount: float | None = Field(alias="totalAmount")
    currency: str | None
    source: str
    item_count: int = Field(alias="itemCount")

    @field_serializer("purchased_at")
    def _ts(self, value: datetime | None) -> str | None:
        return iso_z(value)


class AnalyticsSummary(BaseModel):
    # ── legacy fields kept for the existing frontend (unchanged names) ──
    total_pantry_items: int = Field(alias="totalPantryItems")
    expiring_soon: int = Field(alias="expiringSoon")
    running_low: int = Field(alias="runningLow")
    high_risk: int = Field(alias="highRisk")
    consumed_last_30d_events: int = Field(alias="consumedLast30dEvents")
    consumed_last_30d_quantity: float = Field(alias="consumedLast30dQuantity")
    waste_logs: int = Field(alias="wasteLogs")
    waste_estimated_value: float | None = Field(alias="wasteEstimatedValue")

    # ── richer, always-honest analytics ───────────────────────────────
    currency: str
    # items currently "at risk" (expiring soon or high risk)
    at_risk_items: int = Field(alias="atRiskItems")
    # real money only — NULL when no at-risk item has a recorded price
    at_risk_known_value: float | None = Field(alias="atRiskKnownValue")
    at_risk_value_unavailable_count: int = Field(alias="atRiskValueUnavailableCount")
    total_purchase_value: float | None = Field(alias="totalPurchaseValue")
    known_value_saved: float | None = Field(alias="knownValueSaved")
    waste_quantity: float | None = Field(alias="wasteQuantity")
    recent_consumption: list[ConsumptionEventOut] = Field(alias="recentConsumption")
    recent_waste: list[WasteEventOut] = Field(alias="recentWaste")
    recent_purchases: list[RecentPurchaseOut] = Field(alias="recentPurchases")
