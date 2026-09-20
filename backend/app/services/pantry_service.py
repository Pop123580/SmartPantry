"""Pantry DB ↔ risk-engine glue: find-or-create foods, assess items,
serialize exactly to the frontend ``PantryItem`` shape."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ConsumptionLog, Food, PantryItem, User, utcnow
from app.schemas.pantry import PantryItemOut
from app.services import risk_engine
from app.services.units import (
    canonical_food_key,
    canonical_food_name,
    canonical_unit,
    categorize,
)

CONSUMPTION_WINDOW_DAYS = 30


def find_or_create_food(
    db: Session, *, name: str, category: str | None, default_unit: str | None
) -> Food:
    """Food rows are unique by canonical (plural-insensitive) name, so
    ``Tomatoes`` and ``tomato`` share one catalogue entry."""
    display = canonical_food_name(name)
    key = canonical_food_key(display)
    first_word = (
        display.split()[0].replace("%", r"\%").replace("_", r"\_") if display else ""
    )
    candidates = db.scalars(
        select(Food).where(Food.name.ilike(f"{first_word}%", escape="\\"))
    ).all()
    for food in candidates:
        if canonical_food_key(food.name) == key:
            return food
    category = category or categorize(name)
    food = Food(
        name=display,
        category=category,
        default_unit=canonical_unit(default_unit),
        perishability_score=risk_engine.estimate_perishability(name, category),
    )
    db.add(food)
    db.flush()
    return food


def consumption_counts(db: Session, user_id: UUID) -> dict[UUID, int]:
    """pantry_item_id → consumption events in the last 30 days."""
    since = utcnow() - timedelta(days=CONSUMPTION_WINDOW_DAYS)
    rows = db.execute(
        select(ConsumptionLog.pantry_item_id, func.count())
        .where(ConsumptionLog.user_id == user_id)
        .where(ConsumptionLog.consumed_at >= since)
        .where(ConsumptionLog.pantry_item_id.is_not(None))
        .group_by(ConsumptionLog.pantry_item_id)
    ).all()
    return {pid: int(count) for pid, count in rows}


def assess_item(
    db: Session, item: PantryItem, counts: dict[UUID, int] | None = None
) -> risk_engine.RiskAssessment:
    counts = counts if counts is not None else consumption_counts(db, item.user_id)
    return risk_engine.assess(
        quantity=item.quantity,
        unit=item.unit,
        perishability_score=item.food.perishability_score,
        expires_at=item.expiry_date,
        consumption_events_30d=counts.get(item.id, 0),
        now=utcnow(),
    )


def to_out(
    db: Session, item: PantryItem, counts: dict[UUID, int] | None = None
) -> PantryItemOut:
    assessment = assess_item(db, item, counts)
    return PantryItemOut(
        id=item.id,
        name=item.food.name,
        quantity=item.quantity,
        unit=item.unit,
        category=item.food.category,
        status=assessment.status.value,
        risk=assessment.risk.value,
        expiresAt=item.expiry_date,
        imageUrl=item.image_url,
    )


def list_user_pantry(db: Session, user: User) -> list[PantryItem]:
    return list(
        db.scalars(
            select(PantryItem)
            .where(PantryItem.user_id == user.id)
            .order_by(
                PantryItem.expiry_date.is_(None),
                PantryItem.expiry_date.asc(),
                PantryItem.created_at.asc(),
            )
        )
    )


def serialize_pantry(db: Session, user: User) -> list[tuple[PantryItem, PantryItemOut]]:
    """Every item with its risk assessment, ordered soonest-expiry first."""
    items = list_user_pantry(db, user)
    counts = consumption_counts(db, user.id)
    return [(item, to_out(db, item, counts)) for item in items]


def get_owned_item(db: Session, user: User, item_id: UUID) -> PantryItem | None:
    """Ownership check — callers turn ``None`` into 404 (never 403 w/ data)."""
    return db.scalar(
        select(PantryItem).where(
            PantryItem.id == item_id, PantryItem.user_id == user.id
        )
    )
