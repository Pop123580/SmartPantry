from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WasteLog(Base):
    """Food thrown away — optionally recorded when a pantry item with an
    ``?reason=`` is deleted."""

    __tablename__ = "waste_logs"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pantry_item_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("pantry_items.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    # Snapshot of the food name so history survives pantry-item deletion.
    food_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    reason: Mapped[str] = mapped_column(sa.String(200), nullable=False, default="expired")
    estimated_value: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(10, 2), nullable=True
    )
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)
