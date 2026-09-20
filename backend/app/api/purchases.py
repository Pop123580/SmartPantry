"""Purchase history — created by checkout (and, later, receipt import)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbDep
from app.models import Purchase, PurchaseItem
from app.schemas.purchase import PurchaseOut, PurchaseSummaryOut

router = APIRouter(prefix="/api/purchases", tags=["purchases"])


def _to_out(purchase: Purchase) -> PurchaseOut:
    return PurchaseOut(
        id=purchase.id,
        purchasedAt=purchase.purchased_at,
        totalAmount=float(purchase.total_amount) if purchase.total_amount is not None else None,
        currency=purchase.currency,
        source=purchase.source,
        receiptUrl=purchase.receipt_url,
        createdAt=purchase.created_at,
        items=[
            {
                "id": i.id,
                "name": i.name,
                "quantity": i.quantity,
                "unit": i.unit,
                "unitPrice": float(i.unit_price) if i.unit_price is not None else None,
                "totalPrice": float(i.total_price) if i.total_price is not None else None,
                "category": i.category,
            }
            for i in purchase.items
        ],
    )


@router.get(
    "",
    response_model=list[PurchaseSummaryOut],
    summary="Purchase history",
    description="Newest first. ``totalAmount`` is ``null`` whenever the "
    "purchase was recorded without real prices — never an estimate.",
    responses={401: {"description": "Missing/invalid token"}},
)
def list_purchases(
    current_user: CurrentUser,
    db: DbDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[PurchaseSummaryOut]:
    rows = db.execute(
        select(Purchase, func.count(PurchaseItem.id))
        .outerjoin(PurchaseItem, PurchaseItem.purchase_id == Purchase.id)
        .where(Purchase.user_id == current_user.id)
        .group_by(Purchase.id)
        .order_by(Purchase.purchased_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        PurchaseSummaryOut(
            id=p.id,
            purchasedAt=p.purchased_at,
            totalAmount=float(p.total_amount) if p.total_amount is not None else None,
            currency=p.currency,
            source=p.source,
            itemCount=int(count),
        )
        for p, count in rows
    ]


@router.get(
    "/{purchase_id}",
    response_model=PurchaseOut,
    summary="One purchase with its line items",
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Not found (or owned by another user)"},
    },
)
def get_purchase(
    purchase_id: UUID, current_user: CurrentUser, db: DbDep
) -> PurchaseOut:
    purchase = db.scalar(
        select(Purchase).where(
            Purchase.id == purchase_id, Purchase.user_id == current_user.id
        )
    )
    if purchase is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase not found")
    return _to_out(purchase)
