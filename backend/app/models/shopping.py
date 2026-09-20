from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(
        sa.Float, sa.CheckConstraint("quantity > 0"), nullable=False, default=1
    )
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pcs")
    reason: Mapped[str | None] = mapped_column(sa.String(300), nullable=True)
    # Optional real price per unit — recorded at checkout into the purchase.
    unit_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    in_inventory: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    image_url: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)

    owner = relationship("User", back_populates="shopping_items")
