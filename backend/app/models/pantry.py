from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Food(Base):
    """Catalogue of food types. One row per unique food name (case-folded
    at the service layer); ``perishability_score`` drives the risk engine.

    score: 1 (dry staples such as rice) → 10 (leafy greens)."""

    __tablename__ = "foods"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(sa.String(160), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(sa.String(80), nullable=False, default="Other")
    default_unit: Mapped[str] = mapped_column(
        sa.String(20), nullable=False, default="pcs"
    )
    perishability_score: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=5
    )
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)

    pantry_items = relationship("PantryItem", back_populates="food")


class PantryItem(Base):
    __tablename__ = "pantry_items"
    __table_args__ = (
        sa.Index("ix_pantry_items_user_food", "user_id", "food_id"),
        sa.Index("ix_pantry_items_user_expiry", "user_id", "expiry_date"),
    )

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("foods.id"), nullable=False, index=True
    )
    # Never negative — enforced by a CHECK constraint (migration 0002) and
    # by the cook/checkout application logic.
    quantity: Mapped[float] = mapped_column(
        sa.Float, sa.CheckConstraint("quantity >= 0"), nullable=False
    )
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pcs")
    purchase_date = mapped_column(sa.DateTime, nullable=False)
    expiry_date = mapped_column(sa.DateTime, nullable=True)
    storage_location: Mapped[str] = mapped_column(
        sa.String(50), nullable=False, default="pantry"
    )
    image_url: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    # Optional real money data — set by checkout/receipt flows; manual
    # pantry entries may leave it NULL ("value unknown", never estimated).
    purchase_price: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(12, 2), nullable=True
    )  # per `unit`
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    purchase_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True
    )
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    updated_at = mapped_column(
        sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )

    owner = relationship("User", back_populates="pantry_items")
    food = relationship("Food", back_populates="pantry_items", lazy="joined")
