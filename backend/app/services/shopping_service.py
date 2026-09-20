"""Shopping list logic: inventory awareness and transactional checkout."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    PantryItem,
    Purchase,
    PurchaseItem,
    ShoppingItem,
    User,
    utcnow,
)
from app.schemas.shopping import CreateShoppingItemDTO
from app.services import pantry_service, risk_engine
from app.services.units import canonical_unit, convert, names_match

logger = logging.getLogger(__name__)

IN_STOCK_REASON = "Already available in pantry"
DEFAULT_REASON = "Running low"


class ShoppingListEmpty(Exception):
    pass


class ShoppingItemNotFound(Exception):
    pass


class CheckoutFailed(Exception):
    """Unexpected DB failure during checkout; the transaction was rolled
    back, so no partial state was saved."""


# ── inventory awareness ──────────────────────────────────────────────


def matching_pantry_items(db: Session, user: User, name: str) -> list[PantryItem]:
    """All of the user's pantry items whose food name matches ``name``."""
    return [
        item
        for item in pantry_service.list_user_pantry(db, user)
        if names_match(item.food.name, name)
    ]


def available_quantity(
    matches: list[PantryItem], *, in_unit: str
) -> float | None:
    """Total stock expressed in ``in_unit`` (``None`` if unit family unknown)."""
    total = 0.0
    matched_any = False
    for item in matches:
        converted = convert(item.quantity, item.unit, in_unit)
        if converted is not None:
            total += converted
            matched_any = True
    return total if matched_any else None


# ── list operations ──────────────────────────────────────────────────


def list_items(db: Session, user: User) -> list[ShoppingItem]:
    items = list(
        db.scalars(
            select(ShoppingItem)
            .where(ShoppingItem.user_id == user.id)
            .order_by(ShoppingItem.created_at.asc())
        )
    )
    # Refresh ``in_inventory`` so the flag is always truthful.
    for item in items:
        matches = matching_pantry_items(db, user, item.name)
        available = available_quantity(matches, in_unit=item.unit)
        item.in_inventory = available is not None and available >= item.quantity - 1e-9
    return items


def add_item(db: Session, user: User, dto: CreateShoppingItemDTO) -> ShoppingItem:
    """Create a shopping item; the server decides ``inInventory`` + reason
    (the frontend never overrides inventory truth). Price is optional."""
    matches = matching_pantry_items(db, user, dto.name)
    available = available_quantity(matches, in_unit=dto.unit)
    in_inventory = available is not None and available >= dto.quantity - 1e-9

    if in_inventory:
        reason = IN_STOCK_REASON
    elif available is not None and available > 0:
        reason = f"Only {available:g} {dto.unit} left in pantry"
    else:
        reason = dto.reason or DEFAULT_REASON

    item = ShoppingItem(
        user_id=user.id,
        name=" ".join(dto.name.split()),
        quantity=dto.quantity,
        unit=canonical_unit(dto.unit),
        reason=reason,
        in_inventory=in_inventory,
        image_url=dto.image_url,
        unit_price=dto.unit_price,
        currency=dto.currency,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_owned_item(db: Session, user: User, item_id: UUID) -> ShoppingItem | None:
    return db.scalar(
        select(ShoppingItem).where(
            ShoppingItem.id == item_id, ShoppingItem.user_id == user.id
        )
    )


def delete_item(db: Session, user: User, item_id: UUID) -> None:
    item = get_owned_item(db, user, item_id)
    if item is None:
        raise ShoppingItemNotFound(str(item_id))
    db.delete(item)
    db.commit()


# ── checkout ─────────────────────────────────────────────────────────


def checkout(
    db: Session, user: User, item_ids: list[UUID] | None = None
) -> tuple[Purchase, list[PantryItem], int]:
    """Buy the shopping list in ONE atomic transaction:

    validate → create Purchase → create PurchaseItems → merge into pantry
    → clear bought shopping items → commit.
    Any failure rolls back EVERYTHING — no partial purchases, no orphan
    stock, no half-cleared lists.
    """
    query = select(ShoppingItem).where(ShoppingItem.user_id == user.id)
    if item_ids:
        query = query.where(ShoppingItem.id.in_(item_ids))
    items = list(db.scalars(query))
    if item_ids and len(items) != len(set(item_ids)):
        raise ShoppingItemNotFound("one or more items do not belong to you")
    if not items:
        raise ShoppingListEmpty
    for item in items:  # defence in depth — DTOs already enforce this
        if item.quantity <= 0:
            raise CheckoutFailed(f"Invalid quantity on '{item.name}'")

    settings = get_settings()
    currency = next(
        (i.currency for i in items if i.currency), None
    ) or settings.default_currency

    try:
        # 1-2. purchase + purchase items (prices only when actually known)
        line_totals = [
            (Decimal(str(i.quantity)) * i.unit_price)
            for i in items
            if i.unit_price is not None
        ]
        purchase = Purchase(
            user_id=user.id,
            purchased_at=utcnow(),
            total_amount=sum(line_totals) if line_totals else None,
            currency=currency,
            source="checkout",
        )
        db.add(purchase)
        db.flush()

        for shopping in items:
            food = pantry_service.find_or_create_food(
                db, name=shopping.name, category=None, default_unit=shopping.unit
            )
            price = shopping.unit_price
            line_total = (
                (Decimal(str(shopping.quantity)) * price) if price is not None else None
            )
            db.add(
                PurchaseItem(
                    purchase_id=purchase.id,
                    name=shopping.name,
                    quantity=shopping.quantity,
                    unit=shopping.unit,
                    unit_price=price,
                    total_price=line_total,
                    category=food.category,
                )
            )

        # 3. pantry upserts (one merge per shopping item)
        touched_item_ids: list[UUID] = []
        for shopping in items:
            pantry_item = _merge_into_pantry(db, user, shopping, purchase)
            touched_item_ids.append(pantry_item.id)
            db.delete(shopping)

        db.flush()
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Checkout failed for user %s — rolled back", user.id)
        raise CheckoutFailed(str(exc)) from exc

    pantry_items = list(
        db.scalars(select(PantryItem).where(PantryItem.id.in_(touched_item_ids)))
    )
    return purchase, pantry_items, len(items)


def _merge_into_pantry(
    db: Session, user: User, shopping: ShoppingItem, purchase: Purchase
) -> PantryItem:
    food = pantry_service.find_or_create_food(
        db, name=shopping.name, category=None, default_unit=shopping.unit
    )
    existing = db.scalars(
        select(PantryItem).where(
            PantryItem.user_id == user.id, PantryItem.food_id == food.id
        )
    ).all()

    # Merge into the compatible item whose expiry is furthest out
    # (NULL expiry = no-expiry staples preferred for topping up).
    for item in sorted(
        existing, key=lambda i: (i.expiry_date is None, i.expiry_date), reverse=True
    ):
        incoming = convert(shopping.quantity, shopping.unit, item.unit)
        if incoming is None:
            continue
        item.quantity = item.quantity + incoming
        if shopping.unit_price is not None:  # newest real price wins…
            # …but the price must be expressed per the ITEM's unit:
            # ₹40/kg merged into a grams row is ₹0.04/g, never ₹40/g.
            factor = convert(1, item.unit, shopping.unit)
            if factor is not None:
                item.purchase_price = Decimal(str(shopping.unit_price)) * Decimal(
                    str(factor)
                )
                item.currency = shopping.currency
        item.purchase_id = purchase.id
        db.add(item)
        db.flush()
        return item

    item = PantryItem(
        user_id=user.id,
        food_id=food.id,
        quantity=shopping.quantity,
        unit=canonical_unit(shopping.unit),
        purchase_date=utcnow(),
        expiry_date=utcnow()
        + timedelta(
            days=risk_engine.default_shelf_life_days(food.perishability_score)
        ),
        storage_location="pantry",
        image_url=shopping.image_url,
        purchase_price=shopping.unit_price,
        currency=shopping.currency,
        purchase_id=purchase.id,
    )
    db.add(item)
    db.flush()
    return item
