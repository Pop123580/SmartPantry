"""Shopping list endpoints — inventory-aware, transactional checkout."""

from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, status

from app.dependencies import CurrentUser, DbDep
from app.schemas.shopping import CheckoutResult, CreateShoppingItemDTO, ShoppingItemOut
from app.services import pantry_service, shopping_service

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


def _to_out(item) -> ShoppingItemOut:
    return ShoppingItemOut(
        id=item.id,
        name=item.name,
        quantity=item.quantity,
        unit=item.unit,
        reason=item.reason,
        inInventory=item.in_inventory,
        imageUrl=item.image_url,
        unitPrice=float(item.unit_price) if item.unit_price is not None else None,
        currency=item.currency,
    )


@router.get(
    "",
    response_model=list[ShoppingItemOut],
    summary="List shopping items",
    description="The ``inInventory`` flag is recomputed against the live "
    "pantry on every read, so it's always truthful.",
    responses={401: {"description": "Missing/invalid token"}},
)
def list_shopping(current_user: CurrentUser, db: DbDep) -> list[ShoppingItemOut]:
    return [_to_out(i) for i in shopping_service.list_items(db, current_user)]


@router.post(
    "",
    response_model=ShoppingItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a shopping item",
    description="The server checks the pantry: when enough stock exists the "
    "item is stored with ``inInventory: true`` and reason "
    "'Already available in pantry'.",
    responses={
        401: {"description": "Missing/invalid token"},
        422: {"description": "Validation error"},
    },
)
def add_shopping_item(
    payload: CreateShoppingItemDTO, current_user: CurrentUser, db: DbDep
) -> ShoppingItemOut:
    return _to_out(shopping_service.add_item(db, current_user, payload))


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a shopping item",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Not found (or owned by another user)"},
    },
)
def delete_shopping_item(item_id: UUID, current_user: CurrentUser, db: DbDep) -> None:
    try:
        shopping_service.delete_item(db, current_user, item_id)
    except shopping_service.ShoppingItemNotFound:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Shopping item not found"
        ) from None


@router.post(
    "/checkout",
    response_model=CheckoutResult,
    summary="Buy the shopping list",
    description="Validates the list, creates a purchase record, merges every "
    "item into the pantry (adding quantities when the food already exists, "
    "estimating expiry from perishability otherwise) and clears the bought "
    "items — all inside one transaction.",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "One or more supplied item ids were not found"},
        409: {"description": "Shopping list is empty"},
    },
)
def checkout(
    current_user: CurrentUser,
    db: DbDep,
    item_ids: list[UUID] | None = Body(
        default=None,
        description="Optionally check out only these shopping item ids",
        examples=[["f47ac10b-58cc-4372-a567-0e02b2c3d479"]],
    ),
) -> CheckoutResult:
    try:
        purchase, pantry_items, cleared = shopping_service.checkout(
            db, current_user, item_ids
        )
    except shopping_service.ShoppingListEmpty:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Shopping list is empty"
        ) from None
    except shopping_service.ShoppingItemNotFound as exc:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from None
    except shopping_service.CheckoutFailed as exc:
        # Everything already rolled back inside the service — respond
        # without internals (the full error is logged server-side).
        db.rollback()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Checkout could not be completed — nothing was saved.",
        ) from exc

    return CheckoutResult(
        purchaseId=purchase.id,
        clearedItems=cleared,
        pantry=[pantry_service.to_out(db, item) for item in pantry_items],
        message=f"{cleared} item(s) added to pantry",
    )
