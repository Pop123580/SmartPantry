"""ORM models. All timestamps are stored as naive UTC datetimes
(``DateTime(timezone=False)``) so behaviour is identical on PostgreSQL
and on the SQLite database used by the test-suite; serializers append
the ``Z`` suffix when emitting ISO-8601 to the frontend.
"""

from datetime import UTC, datetime

from app.models.consumption import ConsumptionLog
from app.models.pantry import Food, PantryItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.recipe import Recipe, RecipeIngredient
from app.models.shopping import ShoppingItem
from app.models.user import User
from app.models.waste import WasteLog


def utcnow() -> datetime:
    """Naive UTC now — the single way timestamps are produced."""
    return datetime.now(UTC).replace(tzinfo=None)


__all__ = [
    "utcnow",
    "User",
    "Food",
    "PantryItem",
    "Recipe",
    "RecipeIngredient",
    "ShoppingItem",
    "ConsumptionLog",
    "WasteLog",
    "Purchase",
    "PurchaseItem",
]
