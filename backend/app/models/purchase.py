from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Purchase(Base):
    """A recorded purchase (created by shopping checkout today; a receipt
    confirmation flow can attach ``receipt_url`` + ``source='receipt'``)."""

    __tablename__ = "purchases"
    __table_args__ = (
        sa.Index("ix_purchases_user_time", "user_id", "purchased_at"),
    )

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Money is optional everywhere: totals are stored ONLY when real
    # per-item prices were recorded. ``None`` means "value unknown" and is
    # never substituted with estimates.
    total_amount: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(sa.String(3), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False)
    source: Mapped[str] = mapped_column(
        sa.String(30), nullable=False, default="checkout"
    )  # checkout | receipt | manual
    receipt_url: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)

    owner = relationship("User", back_populates="purchases")
    # selectin: collection eager-load that never multiplies parent rows
    # (safer than "joined" for list endpoints).
    items = relationship(
        "PurchaseItem",
        back_populates="purchase",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PurchaseItem(Base):
    """One line of a purchase — the durable, price-aware history."""

    __tablename__ = "purchase_items"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    purchase_id: Mapped[UUID] = mapped_column(
        sa.Uuid,
        sa.ForeignKey("purchases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pcs")
    unit_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    total_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 2), nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String(80), nullable=True)
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)

    purchase = relationship("Purchase", back_populates="items")
