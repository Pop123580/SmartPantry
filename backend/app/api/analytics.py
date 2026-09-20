"""Dashboard analytics — computed ONLY from real persisted data.

Money rules (review spec §6):
* A monetary figure is returned ONLY when it is derived from recorded
  prices (pantry ``purchase_price`` set by checkout/receipt flows, or
  purchase ``total_amount``).
* When prices are missing the field is ``null`` and companion counters
  (``atRiskValueUnavailableCount``) tell the UI to say "value unavailable"
  instead of inventing numbers.
"""

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.config import get_settings
from app.dependencies import CurrentUser, DbDep
from app.models import ConsumptionLog, Purchase, PurchaseItem, WasteLog, utcnow
from app.schemas.analytics import AnalyticsSummary
from app.services import pantry_service
from app.services.risk_engine import Risk, Status

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

RECENT_LIMIT = 5


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Pantry/consumption/waste/value snapshot",
    description="Real-data-only analytics: risk distribution, 30-day "
    "consumption, waste totals, purchase value, value saved (only where "
    "real prices exist) and recent activity. Monetary fields are ``null`` "
    "when no recorded prices support them — never estimates.",
    responses={401: {"description": "Missing/invalid token"}},
)
def summary(current_user: CurrentUser, db: DbDep) -> AnalyticsSummary:
    settings = get_settings()
    assessed = pantry_service.serialize_pantry(db, current_user)
    outs = [out for _item, out in assessed]

    # ── money at risk: known value vs unknown ─────────────────────────
    at_risk = [
        (item, out)
        for item, out in assessed
        if out.status == Status.EXPIRING_SOON or out.risk == Risk.HIGH
    ]
    priced = [
        (item.quantity * float(item.purchase_price))
        for item, _out in at_risk
        if item.purchase_price is not None
    ]
    at_risk_known_value: float | None = round(sum(priced), 2) if priced else None
    at_risk_unknown_count = sum(
        1 for item, _out in at_risk if item.purchase_price is None
    )

    # ── consumption (30 d) ────────────────────────────────────────────
    thirty_days_ago = utcnow() - timedelta(days=30)
    consumed_events, consumed_qty = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(ConsumptionLog.quantity_used), 0.0),
        )
        .where(ConsumptionLog.user_id == current_user.id)
        .where(ConsumptionLog.consumed_at >= thirty_days_ago)
    ).one()

    # ── value saved: consumed qty × REAL recorded price of that stock ──
    from app.models import PantryItem  # local import keeps the SQL readable

    price_by_item = {
        item.id: float(item.purchase_price)
        for item in db.scalars(
            select(PantryItem).where(
                PantryItem.user_id == current_user.id,
                PantryItem.purchase_price.is_not(None),
            )
        )
    }
    # The log references the same pantry_item_id that carried the price, so
    # only logs backed by a real recorded price contribute — the rest stay
    # "unknown" rather than being estimated.
    log_rows = db.execute(
        select(ConsumptionLog.pantry_item_id, ConsumptionLog.quantity_used).where(
            ConsumptionLog.user_id == current_user.id
        )
    ).all()
    saved_total, saved_any = 0.0, False
    for item_id, qty_used in log_rows:
        price = price_by_item.get(item_id) if item_id else None
        if price is not None:
            saved_total += qty_used * price
            saved_any = True

    # ── waste ─────────────────────────────────────────────────────────
    waste_events, waste_qty, waste_value = db.execute(
        select(
            func.count(),
            func.sum(WasteLog.quantity),
            func.sum(WasteLog.estimated_value),
        ).where(WasteLog.user_id == current_user.id)
    ).one()

    # ── purchases (real recorded totals only) ─────────────────────────
    total_purchase_value = db.scalar(
        select(func.sum(Purchase.total_amount)).where(
            Purchase.user_id == current_user.id,
            Purchase.total_amount.is_not(None),
        )
    )

    recent_consumption = db.scalars(
        select(ConsumptionLog)
        .where(ConsumptionLog.user_id == current_user.id)
        .order_by(ConsumptionLog.consumed_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    recent_waste = db.scalars(
        select(WasteLog)
        .where(WasteLog.user_id == current_user.id)
        .order_by(WasteLog.created_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    recent_purchases_rows = db.execute(
        select(Purchase, func.count(PurchaseItem.id))
        .outerjoin(PurchaseItem, PurchaseItem.purchase_id == Purchase.id)
        .where(Purchase.user_id == current_user.id)
        .group_by(Purchase.id)
        .order_by(Purchase.purchased_at.desc())
        .limit(RECENT_LIMIT)
    ).all()

    return AnalyticsSummary(
        # legacy fields (unchanged for the existing frontend)
        totalPantryItems=len(outs),
        expiringSoon=sum(1 for o in outs if o.status == Status.EXPIRING_SOON),
        runningLow=sum(1 for o in outs if o.status == Status.RUNNING_LOW),
        highRisk=sum(1 for o in outs if o.risk == Risk.HIGH),
        consumedLast30dEvents=int(consumed_events or 0),
        consumedLast30dQuantity=float(consumed_qty or 0.0),
        wasteLogs=int(waste_events or 0),
        wasteEstimatedValue=(
            float(waste_value) if waste_value is not None else None
        ),
        # honest value analytics
        currency=settings.default_currency,
        atRiskItems=len(at_risk),
        atRiskKnownValue=at_risk_known_value,
        atRiskValueUnavailableCount=at_risk_unknown_count,
        totalPurchaseValue=(
            float(total_purchase_value)
            if total_purchase_value is not None
            else None
        ),
        knownValueSaved=round(saved_total, 2) if saved_any else None,
        wasteQuantity=float(waste_qty) if waste_qty is not None else None,
        recentConsumption=[
            {
                "name": log.food_name,
                "quantity": log.quantity_used,
                "unit": log.unit,
                "consumedAt": log.consumed_at,
                "recipeId": log.recipe_id,
            }
            for log in recent_consumption
        ],
        recentWaste=[
            {
                "name": log.food_name,
                "quantity": log.quantity,
                "unit": log.unit,
                "reason": log.reason,
                "estimatedValue": (
                    float(log.estimated_value)
                    if log.estimated_value is not None
                    else None
                ),
                "createdAt": log.created_at,
            }
            for log in recent_waste
        ],
        recentPurchases=[
            {
                "id": p.id,
                "purchasedAt": p.purchased_at,
                "totalAmount": (
                    float(p.total_amount) if p.total_amount is not None else None
                ),
                "currency": p.currency,
                "source": p.source,
                "itemCount": int(count),
            }
            for p, count in recent_purchases_rows
        ],
    )
