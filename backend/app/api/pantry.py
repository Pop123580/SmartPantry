"""Pantry CRUD — every item is scoped to the JWT-authenticated user.

Response shape is EXACTLY the frontend ``PantryItem`` interface:
``{id, name, quantity, unit, category, status, risk, expiresAt, imageUrl}``.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbDep
from app.models import PantryItem, WasteLog, utcnow
from app.schemas.pantry import CreatePantryItemDTO, PantryItemOut, UpdatePantryItemDTO
from app.services import pantry_service
from app.services.units import canonical_unit

router = APIRouter(prefix="/api/pantry", tags=["pantry"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Pantry item not found"
)


def _get_owned_or_404(db, user, item_id: UUID) -> PantryItem:
    """Ownership is enforced here: another user's item yields 404 and is
    indistinguishable from a non-existent id."""
    item = pantry_service.get_owned_item(db, user, item_id)
    if item is None:
        raise _NOT_FOUND
    return item


@router.get(
    "",
    response_model=list[PantryItemOut],
    summary="List my pantry",
    description="All items for the authenticated user, soonest-expiring "
    "first, each with deterministic ``status``/``risk`` from the risk engine.",
    responses={401: {"description": "Missing/invalid token"}},
)
def list_pantry(current_user: CurrentUser, db: DbDep) -> list[PantryItemOut]:
    return [out for _item, out in pantry_service.serialize_pantry(db, current_user)]


@router.get(
    "/{item_id}",
    response_model=PantryItemOut,
    summary="Get one pantry item",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Not found (or owned by another user)"},
    },
)
def get_pantry_item(item_id: UUID, current_user: CurrentUser, db: DbDep) -> PantryItemOut:
    item = _get_owned_or_404(db, current_user, item_id)
    return pantry_service.to_out(db, item)


@router.post(
    "",
    response_model=PantryItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a pantry item",
    description="Creates (or reuses) the food catalogue entry, estimates "
    "perishability for new foods, and returns the assessed item.",
    responses={
        401: {"description": "Missing/invalid token"},
        422: {"description": "Validation error"},
    },
)
def create_pantry_item(
    payload: CreatePantryItemDTO, current_user: CurrentUser, db: DbDep
) -> PantryItemOut:
    food = pantry_service.find_or_create_food(
        db, name=payload.name, category=payload.category, default_unit=payload.unit
    )
    item = PantryItem(
        user_id=current_user.id,
        food_id=food.id,
        quantity=payload.quantity,
        unit=canonical_unit(payload.unit),
        purchase_date=utcnow(),
        expiry_date=payload.expires_at,
        storage_location=payload.storage_location or "pantry",
        image_url=payload.image_url,
        purchase_price=payload.purchase_price,
        currency=payload.currency,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return pantry_service.to_out(db, item)


@router.patch(
    "/{item_id}",
    response_model=PantryItemOut,
    summary="Update a pantry item",
    description="Partial update — only the fields present in the body change.",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Not found (or owned by another user)"},
        422: {"description": "Validation error"},
    },
)
def update_pantry_item(
    item_id: UUID,
    payload: UpdatePantryItemDTO,
    current_user: CurrentUser,
    db: DbDep,
) -> PantryItemOut:
    item = _get_owned_or_404(db, current_user, item_id)
    changes = payload.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"]:
        item.food = pantry_service.find_or_create_food(
            db,
            name=changes["name"],
            category=changes.get("category") or item.food.category,
            default_unit=item.unit,
        )
    if "category" in changes and changes["category"]:
        item.food.category = changes["category"]
    if "quantity" in changes and changes["quantity"] is not None:
        item.quantity = changes["quantity"]
    if "unit" in changes and changes["unit"]:
        item.unit = canonical_unit(changes["unit"])
    if "expires_at" in changes:
        item.expiry_date = changes["expires_at"]  # may intentionally be None
    if "image_url" in changes:
        item.image_url = changes["image_url"]
    if "storage_location" in changes and changes["storage_location"]:
        item.storage_location = changes["storage_location"]
    if "purchase_price" in changes:
        item.purchase_price = changes["purchase_price"]
    if "currency" in changes and changes["currency"]:
        item.currency = changes["currency"]

    db.add(item)
    db.commit()
    db.refresh(item)
    return pantry_service.to_out(db, item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a pantry item",
    description="Deletes the item. Pass ``reason`` (e.g. ``expired``) and an "
    "optional estimated ``value`` to record it in the waste log instead of "
    "silently discarding it.",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Not found (or owned by another user)"},
    },
)
def delete_pantry_item(
    item_id: UUID,
    current_user: CurrentUser,
    db: DbDep,
    reason: str | None = Query(default=None, max_length=200),
    value: Decimal | None = Query(default=None, ge=0),
) -> None:
    item = _get_owned_or_404(db, current_user, item_id)
    if reason:
        # Derive value ONLY from a recorded real price or an explicit value
        # the caller passed — no invented numbers.
        estimated = value
        if estimated is None and item.purchase_price is not None:
            estimated = Decimal(str(item.quantity)) * item.purchase_price
        db.add(
            WasteLog(
                user_id=current_user.id,
                pantry_item_id=item.id,
                quantity=item.quantity,
                unit=item.unit,
                food_name=item.food.name,
                reason=reason,
                estimated_value=estimated,
            )
        )
    db.delete(item)
    db.commit()
