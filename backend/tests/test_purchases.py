"""Purchase history: checkout creates Purchase + PurchaseItems with real
prices only; reads are ownership-scoped; unknown money stays NULL."""

from uuid import UUID

from sqlalchemy import select

from app.models import Purchase, PurchaseItem
from tests.conftest import TestingSessionLocal


def _checkout_with_prices(client, headers):
    client.post(
        "/api/shopping",
        headers=headers,
        json={
            "name": "Milk", "quantity": 2, "unit": "l",
            "unitPrice": 62.50, "currency": "INR",
        },
    )
    client.post(
        "/api/shopping",
        headers=headers,
        json={"name": "Curd", "quantity": 400, "unit": "g"},  # no price — ok
    )
    response = client.post("/api/shopping/checkout", headers=headers, json=None)
    assert response.status_code == 200, response.text
    return response.json()


class TestCheckoutCreatesPurchaseGraph:
    def test_purchase_and_items_created_from_real_data(
        self, client, auth_headers
    ):
        headers, _ = auth_headers(email="buy1@example.com")
        result = _checkout_with_prices(client, headers)

        session = TestingSessionLocal()
        try:
            purchase = session.scalar(
                select(Purchase).where(Purchase.id == UUID(result["purchaseId"]))
            )
            assert purchase is not None
            assert purchase.source == "checkout"
            assert purchase.currency == "INR"
            assert float(purchase.total_amount) == 125.00  # 2 × 62.50

            items = session.scalars(
                select(PurchaseItem).where(PurchaseItem.purchase_id == purchase.id)
            ).all()
            assert {i.name for i in items} == {"Milk", "Curd"}
            milk = next(i for i in items if i.name == "Milk")
            assert float(milk.unit_price) == 62.50
            assert float(milk.total_price) == 125.00
            assert milk.category == "Dairy"
            curd = next(i for i in items if i.name == "Curd")
            assert curd.unit_price is None and curd.total_price is None
        finally:
            session.close()

    def test_purchase_history_list_and_detail(self, client, auth_headers):
        headers, _ = auth_headers(email="buy2@example.com")
        result = _checkout_with_prices(client, headers)

        history = client.get("/api/purchases", headers=headers)
        assert history.status_code == 200
        assert len(history.json()) == 1
        row = history.json()[0]
        assert row["totalAmount"] == 125
        assert row["currency"] == "INR"
        assert row["source"] == "checkout"
        assert row["itemCount"] == 2

        detail = client.get(f"/api/purchases/{result['purchaseId']}", headers=headers)
        assert detail.status_code == 200
        body = detail.json()
        assert len(body["items"]) == 2
        assert body["purchasedAt"].endswith("Z")

    def test_price_free_checkout_keeps_total_null(self, client, auth_headers):
        headers, _ = auth_headers(email="buy3@example.com")
        client.post(
            "/api/shopping", headers=headers, json={"name": "Banana", "quantity": 6}
        )
        assert client.post("/api/shopping/checkout", headers=headers).status_code == 200
        row = client.get("/api/purchases", headers=headers).json()[0]
        assert row["totalAmount"] is None  # never invented

    def test_purchases_are_ownership_scoped(self, client, auth_headers):
        headers_a, _ = auth_headers(email="buy4a@example.com")
        headers_b, _ = auth_headers(email="buy4b@example.com")
        result = _checkout_with_prices(client, headers_a)

        assert client.get("/api/purchases", headers=headers_b).json() == []
        assert (
            client.get(
                f"/api/purchases/{result['purchaseId']}", headers=headers_b
            ).status_code
            == 404
        )

    def test_stock_and_price_flow_into_pantry(self, client, auth_headers):
        headers, _ = auth_headers(email="buy5@example.com")
        _checkout_with_prices(client, headers)
        pantry = client.get("/api/pantry", headers=headers).json()
        milk = next(i for i in pantry if i["name"] == "Milk")
        assert milk["quantity"] == 2 and milk["unit"] == "l"

    def test_price_converts_with_unit_on_merge(self, client, auth_headers):
        """₹40/kg merged into an existing GRAMS pantry row must become
        ₹0.04/g — the per-unit price follows the item's unit."""
        from app.models import PantryItem

        headers, _ = auth_headers(email="buy6@example.com")
        client.post(
            "/api/pantry",
            headers=headers,
            json={"name": "Tomato", "quantity": 300, "unit": "g"},
        )
        client.post(
            "/api/shopping",
            headers=headers,
            json={
                "name": "Tomato", "quantity": 1, "unit": "kg",
                "unitPrice": 40, "currency": "INR",
            },
        )
        assert (
            client.post("/api/shopping/checkout", headers=headers).status_code
            == 200
        )
        session = TestingSessionLocal()
        try:
            item = session.scalar(select(PantryItem).where(PantryItem.quantity > 0))
            assert item.unit == "g" and item.quantity == 1300
            assert abs(float(item.purchase_price) - 0.04) < 1e-9
            assert item.currency == "INR"
            assert item.purchase_id is not None
        finally:
            session.close()
