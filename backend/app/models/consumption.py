from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConsumptionLog(Base):
    """Written every time food is consumed (e.g. a recipe is cooked)."""

    __tablename__ = "consumption_logs"
    __table_args__ = (sa.Index("ix_consumption_user_time", "user_id", "consumed_at"),)

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pantry_item_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("pantry_items.id", ondelete="SET NULL"), nullable=True
    )
    recipe_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("recipes.id", ondelete="SET NULL"), nullable=True
    )
    quantity_used: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    # Snapshot of the food name so history survives pantry-item deletion.
    food_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    consumed_at = mapped_column(
        sa.DateTime, server_default=sa.func.now(), nullable=False, index=True
    )
