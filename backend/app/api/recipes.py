"""Recipe endpoints — Food Rescue recommendations, details and cooking.

Route order matters: ``/recommended`` is declared before ``/{recipe_id}``.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbDep
from app.schemas.recipe import CookResult, RecipeOut
from app.services import recipe_service

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def _to_out(recipe) -> RecipeOut:
    return RecipeOut(
        id=recipe.id,
        name=recipe.name,
        ingredients=[
            {"name": i.name, "quantity": i.quantity, "unit": i.unit}
            for i in recipe.ingredients
        ],
        reasoning=recipe.reasoning,
        instructions=list(recipe.instructions or []),
        imageUrl=recipe.image_url,
    )


@router.get(
    "/recommended",
    response_model=list[RecipeOut],
    summary="Recommend food-rescue recipes",
    description="Analyzes the user's pantry risk, sends the URGENT items "
    "(plus available stock names) to Amazon Bedrock, validates the AI output "
    "with Pydantic, persists the recipes, and returns them. When AWS is not "
    "configured a deterministic generator produces equivalent, sensible "
    "recommendations from the same risk data.",
    responses={401: {"description": "Missing/invalid token"}},
)
def recommended(
    current_user: CurrentUser,
    db: DbDep,
    limit: int = Query(default=3, ge=1, le=5),
) -> list[RecipeOut]:
    recipes, _source = recipe_service.recommend(db, current_user, max_recipes=limit)
    return [_to_out(r) for r in recipes]


@router.get(
    "/{recipe_id}",
    response_model=RecipeOut,
    summary="Get one recipe",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Recipe not found"},
    },
)
def get_recipe(recipe_id: UUID, current_user: CurrentUser, db: DbDep) -> RecipeOut:
    try:
        recipe = recipe_service.get_recipe(db, current_user, recipe_id)
    except recipe_service.RecipeNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found") from None
    return _to_out(recipe)


@router.post(
    "/{recipe_id}/cook",
    response_model=CookResult,
    summary="Cook a recipe (deducts pantry stock)",
    description="Real transactional operation: matches each ingredient to "
    "pantry items (FEFO order), subtracts the used quantities, writes "
    "consumption logs and returns the updated items with recalculated risk. "
    "Inventory can never go negative — the whole transaction rolls back "
    "with 409 when stock is insufficient.",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Recipe not found"},
        409: {"description": "Insufficient ingredients in pantry"},
    },
)
def cook(recipe_id: UUID, current_user: CurrentUser, db: DbDep) -> CookResult:
    try:
        return recipe_service.cook_recipe(db, current_user, recipe_id)
    except recipe_service.RecipeNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recipe not found") from None
    except recipe_service.InsufficientIngredients as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Not enough stock to cook this recipe",
                "shortfalls": exc.shortfalls,
            },
        ) from None
