from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    email: Mapped[str] = mapped_column(
        sa.String(320), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str | None] = mapped_column(
    sa.String(255),
    nullable=True,
)
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    updated_at = mapped_column(
        sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )

    pantry_items = relationship(
        "PantryItem", back_populates="owner", cascade="all, delete-orphan"
    )
    shopping_items = relationship(
        "ShoppingItem", back_populates="owner", cascade="all, delete-orphan"
    )
    purchases = relationship(
        "Purchase", back_populates="owner", cascade="all, delete-orphan"
    )
