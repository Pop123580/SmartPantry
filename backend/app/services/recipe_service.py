"""Recipe recommendation (Bedrock-first, deterministic fallback) and the
cook flow that deducts stock inside a single database transaction."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConsumptionLog, PantryItem, Recipe, RecipeIngredient, User, utcnow
from app.schemas.recipe import AIRecipe, AIRecipeIngredient, ConsumedItem, CookResult
from app.services import pantry_service, risk_engine
from app.services.bedrock_service import BedrockService, BedrockUnavailable
from app.services.units import canonical_unit, convert, names_match

logger = logging.getLogger(__name__)

MAX_URGENT_ITEMS_SENT_TO_AI = 12
MAX_AVAILABLE_ITEMS_SENT_TO_AI = 25


class RecipeNotFound(Exception):
    pass


class InsufficientIngredients(Exception):
    def __init__(self, shortfalls: list[dict]) -> None:
        super().__init__("Not enough stock to cook this recipe")
        self.shortfalls = shortfalls


# ── context building ─────────────────────────────────────────────────


def _assessed_items(db: Session, user: User) -> list[dict]:
    """Every in-stock item with its risk verdict."""
    items = pantry_service.list_user_pantry(db, user)
    counts = pantry_service.consumption_counts(db, user.id)
    assessed: list[dict] = []
    for item in items:
        if item.quantity <= 0:
            continue
        assessment = pantry_service.assess_item(db, item, counts)
        assessed.append(
            {
                "name": item.food.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "days": assessment.days_until_expiry,
                "risk": assessment.risk.value,
                "is_urgent": assessment.risk == risk_engine.Risk.HIGH
                or assessment.status == risk_engine.Status.EXPIRING_SOON,
            }
        )
    return assessed


def _build_ai_context(assessed: list[dict]) -> tuple[list[dict], list[str]]:
    """Structured context for the LLM — a small curated snapshot, never
    the whole database."""
    urgent = [
        {
            "name": a["name"],
            "quantity": round(a["quantity"], 3),
            "unit": a["unit"],
            "risk": a["risk"],
            "days_until_expiry": (
                round(a["days"], 1) if a["days"] is not None else None
            ),
        }
        for a in assessed
        if a["is_urgent"]
    ][:MAX_URGENT_ITEMS_SENT_TO_AI]
    available = list(
        dict.fromkeys(a["name"] for a in assessed)  # de-dupe, keep order
    )[:MAX_AVAILABLE_ITEMS_SENT_TO_AI]
    return urgent, available


# ── deterministic fallback recipes ───────────────────────────────────

_DISH_BY_COMPANION = (
    (("rice", "poha"), "Rice Bowl"),
    (("bread", "pav", "bun"), "Sandwich"),
    (("pasta",), "Pasta Toss"),
    (("noodle",), "Noodle Stir-Fry"),
    (("tortilla", "roti", "naan"), "Wrap"),
    (("egg",), "Omelette"),
)


def _estimate_portion(quantity: float, unit: str) -> float:
    """A realistic serving amount, never more than what's in stock."""
    unit = canonical_unit(unit)
    if unit == "g":
        return min(quantity, 300.0)
    if unit == "kg":
        return min(quantity, 0.3)
    if unit == "ml":
        return min(quantity, 300.0)
    if unit == "l":
        return min(quantity, 0.5)
    return min(quantity, 3.0)


def _fallback_recipes(assessed: list[dict], max_recipes: int) -> list[AIRecipe]:
    """Deterministic template recipes — guarantees the Food Rescue page
    works even with no AWS configured. Urgent items are always the stars."""
    urgent = sorted(
        (a for a in assessed if a["is_urgent"]),
        key=lambda a: (a["days"] is None, a["days"] or 0.0),
    )
    available = [a for a in assessed if not a["is_urgent"]]
    companion_names = " ".join(a["name"].lower() for a in available)

    dish = "Rescue Stir-Fry"
    for keys, candidate in _DISH_BY_COMPANION:
        if any(key in companion_names for key in keys):
            dish = candidate
            break

    recipes: list[AIRecipe] = []
    used: set[str] = set()
    for star in urgent:
        if len(recipes) >= max_recipes:
            break
        if star["name"] in used:
            continue
        used.add(star["name"])

        second = next(
            (a for a in urgent if a["name"] not in used and a["name"] != star["name"]),
            None,
        )
        if second:
            used.add(second["name"])
            name = f"{star['name']} & {second['name']} {dish}"
        else:
            name = f"{star['name']} {dish}"

        ingredients = [
            AIRecipeIngredient(
                name=star["name"],
                quantity=_estimate_portion(star["quantity"], star["unit"]),
                unit=canonical_unit(star["unit"]),
            )
        ]
        if second:
            ingredients.append(
                AIRecipeIngredient(
                    name=second["name"],
                    quantity=_estimate_portion(second["quantity"], second["unit"]),
                    unit=canonical_unit(second["unit"]),
                )
            )
        for companion in available[:2]:
            ingredients.append(
                AIRecipeIngredient(
                    name=companion["name"],
                    quantity=_estimate_portion(companion["quantity"], companion["unit"]),
                    unit=canonical_unit(companion["unit"]),
                )
            )

        days = star["days"]
        if days is not None and days < 0:
            when = "its expiry date has passed"
        elif days is not None:
            when = f"expires in {max(round(days), 1)} day(s)"
        else:
            when = "is highly perishable"
        reasoning = (
            f"Uses the ingredients most likely to be wasted first: "
            f"{star['name']} ({when})."
        )
        instructions = [
            f"Wash and prep {star['name']} and the remaining ingredients.",
            "Heat a tablespoon of oil in a pan over medium heat.",
            f"Add {star['name']} and cook for 4-5 minutes, stirring often.",
            "Add the remaining ingredients with salt and your favourite spices.",
            "Cook until everything is tender and combined, then serve hot.",
        ]
        recipes.append(
            AIRecipe(
                name=name,
                ingredients=ingredients,
                reasoning=reasoning,
                instructions=instructions,
            )
        )
    return recipes[:max_recipes]


# ── recommendation ───────────────────────────────────────────────────


def recommend(
    db: Session, user: User, max_recipes: int = 3, bedrock: BedrockService | None = None
) -> tuple[list[Recipe], str]:
    """Fresh recommendations for a user, persisted so ``cook`` can run.
    The user's older recommendations are replaced atomically.

    Returns ``(recipes, source)`` where source ∈ {"bedrock", "fallback"}.
    """
    assessed = _assessed_items(db, user)
    if not assessed:
        return [], "fallback"

    urgent, available = _build_ai_context(assessed)

    ai_recipes: list[AIRecipe] | None = None
    source = "fallback"
    bedrock = bedrock or BedrockService()
    if bedrock.enabled:
        try:
            ai_recipes = bedrock.generate_recipes(
                urgent_items=urgent, available_items=available, max_recipes=max_recipes
            )
            source = "bedrock"
            logger.info("Generated %d recipes with Bedrock", len(ai_recipes))
        except BedrockUnavailable as exc:
            logger.info("Bedrock unavailable, using fallback recipes: %s", exc)

    if not ai_recipes:
        ai_recipes = _fallback_recipes(assessed, max_recipes)
        if not ai_recipes and assessed:  # nothing urgent → still suggest something
            top = dict(assessed[0], is_urgent=True)
            ai_recipes = _fallback_recipes([top, *assessed[1:]], 1)

    persisted = persist_recipes(db, user, ai_recipes[:max_recipes])
    return persisted, source


def persist_recipes(db: Session, user: User, ai_recipes: list[AIRecipe]) -> list[Recipe]:
    old_ids = db.scalars(select(Recipe.id).where(Recipe.owner_id == user.id)).all()
    if old_ids:
        db.query(Recipe).filter(Recipe.id.in_(old_ids)).delete(
            synchronize_session=False
        )
    persisted: list[Recipe] = []
    for ai in ai_recipes:
        recipe = Recipe(
            owner_id=user.id,
            name=ai.name,
            reasoning=ai.reasoning,
            instructions=list(ai.instructions),
            image_url=None,
            ingredients=[
                RecipeIngredient(
                    name=i.name,
                    quantity=i.quantity,
                    unit=canonical_unit(i.unit),
                )
                for i in ai.ingredients
            ],
        )
        db.add(recipe)
        persisted.append(recipe)
    db.commit()
    for recipe in persisted:
        db.refresh(recipe)
    return persisted


def get_recipe(db: Session, user: User, recipe_id: UUID) -> Recipe:
    recipe = db.scalar(
        select(Recipe).where(
            Recipe.id == recipe_id,
            (Recipe.owner_id == user.id) | (Recipe.owner_id.is_(None)),
        )
    )
    if recipe is None:
        raise RecipeNotFound(str(recipe_id))
    return recipe


# ── cook flow ────────────────────────────────────────────────────────


def cook_recipe(db: Session, user: User, recipe_id: UUID) -> CookResult:
    """Deduct every ingredient from the user's pantry in ONE transaction.

    * Food-name matching is plural-insensitive; FEFO order (expiring
      first) decides which physical stock leaves first.
    * Quantities are converted between compatible units before comparing.
    * Stock can never go negative — insufficient stock aborts everything.
    """
    recipe = get_recipe(db, user, recipe_id)
    pantry_items = pantry_service.list_user_pantry(db, user)

    consumptions: list[tuple[RecipeIngredient, PantryItem, float]] = []
    shortfalls: list[dict] = []

    for ingredient in recipe.ingredients:
        matches = [
            item
            for item in pantry_items
            if names_match(item.food.name, ingredient.name) and item.quantity > 0
        ]
        matches.sort(key=lambda i: (i.expiry_date is None, i.expiry_date))

        need = ingredient.quantity  # expressed in ingredient.unit
        remaining = need
        for item in matches:
            if remaining <= 1e-9:
                break
            item_qty_in_ing_unit = convert(item.quantity, item.unit, ingredient.unit)
            if item_qty_in_ing_unit is None:
                continue  # incompatible units — this stock can't satisfy
            take_in_ing_unit = min(item_qty_in_ing_unit, remaining)
            take_in_item_unit = convert(take_in_ing_unit, ingredient.unit, item.unit)
            consumptions.append((ingredient, item, take_in_item_unit))
            remaining -= take_in_ing_unit

        if remaining > 1e-6:
            shortfalls.append(
                {
                    "name": ingredient.name,
                    "needed": round(need, 3),
                    "available": round(need - remaining, 3),
                    "unit": ingredient.unit,
                }
            )

    if shortfalls:
        raise InsufficientIngredients(shortfalls)

    cooked_at = utcnow()
    consumed_items: list[ConsumedItem] = []
    consumed_item_ids: set[UUID] = set()
    for _ingredient, item, taken in consumptions:
        # Prevent negative inventory at the application layer; the DB
        # CHECK constraint is the second line of defence.
        item.quantity = max(0.0, round(item.quantity - taken, 6))
        db.add(
            ConsumptionLog(
                user_id=user.id,
                pantry_item_id=item.id,
                recipe_id=recipe.id,
                quantity_used=taken,
                unit=item.unit,
                food_name=item.food.name,
                consumed_at=cooked_at,
            )
        )
        consumed_items.append(
            ConsumedItem(
                pantryItemId=item.id,
                name=item.food.name,
                quantity=taken,
                unit=item.unit,
            )
        )
        consumed_item_ids.add(item.id)

    db.commit()

    # Recalculate risk (fresh read after commit) on everything affected.
    updated = [
        pantry_service.to_out(db, item)
        for item in db.scalars(
            select(PantryItem).where(PantryItem.id.in_(consumed_item_ids))
        )
    ]
    return CookResult(
        recipeId=recipe.id,
        cookedAt=cooked_at,
        consumed=consumed_items,
        updatedPantry=updated,
    )
