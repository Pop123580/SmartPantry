from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Recipe(Base):
    """A generated (Bedrock) or deterministically-built food-rescue recipe.

    ``owner_id`` keeps each user's recommendation feed private without
    changing the public contract (recipes are read-only to other users'.
    """

    __tablename__ = "recipes"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    owner_id: Mapped[UUID | None] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    instructions: Mapped[list] = mapped_column(sa.JSON, nullable=False, default=list)
    image_url: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    created_at = mapped_column(sa.DateTime, server_default=sa.func.now(), nullable=False)

    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[UUID] = mapped_column(sa.Uuid, primary_key=True, default=uuid4)
    recipe_id: Mapped[UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(20), nullable=False, default="pcs")

    recipe = relationship("Recipe", back_populates="ingredients")
