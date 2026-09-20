"""Recipe schemas, incl. the Pydantic models that VALIDATE Bedrock output —
the AI never talks directly to the frontend or the database."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.common import iso_z, tidy_quantity
from app.schemas.pantry import PantryItemOut


class RecipeIngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    quantity: float
    unit: str

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)


class RecipeOut(BaseModel):
    """Matches the frontend ``Recipe`` type (``imageUrl`` camelCase)."""

    id: UUID
    name: str
    ingredients: list[RecipeIngredientOut]
    reasoning: str | None = None
    instructions: list[str] = []
    image_url: str | None = Field(default=None, alias="imageUrl")


class ConsumedItem(BaseModel):
    pantry_item_id: UUID = Field(alias="pantryItemId")
    name: str
    quantity: float
    unit: str

    @field_serializer("quantity")
    def _qty(self, value: float) -> float | int:
        return tidy_quantity(value)


class CookResult(BaseModel):
    """Response of ``POST /api/recipes/{id}/cook``."""

    recipe_id: UUID = Field(alias="recipeId")
    cooked_at: datetime = Field(alias="cookedAt")
    consumed: list[ConsumedItem]
    updated_pantry: list[PantryItemOut] = Field(alias="updatedPantry")

    @field_serializer("cooked_at")
    def _cooked(self, value: datetime) -> str:
        return iso_z(value) or ""


# ── AI output validation (Amazon Bedrock) ────────────────────────────


class AIRecipeIngredient(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0, le=100_000)
    unit: str = Field(min_length=1, max_length=20)


class AIRecipe(BaseModel):
    """One recipe as returned by Bedrock; strictly validated."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=3, max_length=200)
    ingredients: list[AIRecipeIngredient] = Field(min_length=1, max_length=12)
    reasoning: str = Field(min_length=10, max_length=600)
    instructions: list[str] = Field(min_length=2, max_length=12)


class AIRecipeList(BaseModel):
    recipes: list[AIRecipe] = Field(min_length=1, max_length=5)
