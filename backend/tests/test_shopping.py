"""Shopping: add/remove with inventory detection, checkout merging into
the pantry inside one transaction."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import Purchase, ShoppingItem
from tests.conftest import TestingSessionLocal


def _add_tomatoes_to_pantry(client, headers):
    client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Tomato", "quantity": 1, "unit": "kg",
            "category": "Vegetables",
            "expiresAt": (datetime.now(UTC) + timedelta(days=9)).isoformat(),
        },
    )


def test_add_detects_stock_in_pantry(client, auth_headers):
    """Tomatoes 1 kg in pantry → adding Tomatoes 1 kg to the list flags
    inInventory + 'Already available in pantry'."""
    headers, _user = auth_headers(email="shop1@example.com")
    _add_tomatoes_to_pantry(client, headers)

    response = client.post(
        "/api/shopping",
        headers=headers,
        json={"name": "Tomatoes", "quantity": 1, "unit": "kg"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == {
        "id", "name", "quantity", "unit", "reason", "inInventory", "imageUrl",
        "unitPrice", "currency",  # additive real-price fields (null here)
    }
    assert body["inInventory"] is True
    assert body["reason"] == "Already available in pantry"
    assert body["unitPrice"] is None  # no price supplied → stays unknown

    other = client.post(
        "/api/shopping",
        headers=headers,
        json={"name": "Milk", "quantity": 1, "unit": "l"},
    )
    assert other.json()["inInventory"] is False
    assert other.json()["reason"] == "Running low"


def test_add_allows_custom_reason(client, auth_headers):
    headers, _user = auth_headers(email="shop2@example.com")
    response = client.post(
        "/api/shopping",
        headers=headers,
        json={"name": "Eggs", "quantity": 12, "unit": "pcs", "reason": "For baking"},
    )
    assert response.json()["reason"] == "For baking"


def test_list_and_delete(client, auth_headers):
    headers, _user = auth_headers(email="shop3@example.com")
    first = client.post(
        "/api/shopping", headers=headers, json={"name": "Curd", "quantity": 500, "unit": "g"}
    ).json()
    client.post("/api/shopping", headers=headers, json={"name": "Bread", "quantity": 1})

    items = client.get("/api/shopping", headers=headers).json()
    assert len(items) == 2

    assert (
        client.delete(f"/api/shopping/{first['id']}", headers=headers).status_code
        == 204
    )
    items = client.get("/api/shopping", headers=headers).json()
    assert len(items) == 1 and items[0]["name"] == "Bread"

    assert (
        client.delete(f"/api/shopping/{first['id']}", headers=headers).status_code
        == 404
    )


def test_checkout_merges_into_pantry_and_clears_list(client, auth_headers):
    headers, _user = auth_headers(email="shop4@example.com")
    _add_tomatoes_to_pantry(client, headers)
    client.post(
        "/api/shopping", headers=headers, json={"name": "Tomato", "quantity": 1, "unit": "kg"}
    )
    client.post(
        "/api/shopping", headers=headers, json={"name": "Milk", "quantity": 1, "unit": "l"}
    )

    bought = client.post("/api/shopping/checkout", headers=headers, json=None)
    assert bought.status_code == 200, bought.text
    result = bought.json()
    assert result["clearedItems"] == 2
    assert result["purchaseId"]

    # Tomato merged into existing row (1 kg → 2 kg); Milk is a new row
    pantry = client.get("/api/pantry", headers=headers).json()
    tomato = next(i for i in pantry if i["name"].lower() == "tomato")
    assert tomato["quantity"] == 2
    assert tomato["unit"] == "kg"
    milk = next(i for i in pantry if i["name"].lower() == "milk")
    assert milk["quantity"] == 1 and milk["unit"] == "l"
    assert milk["expiresAt"] is not None  # shelf-life estimated on checkout

    # list cleared, purchase recorded
    assert client.get("/api/shopping", headers=headers).json() == []
    session = TestingSessionLocal()
    try:
        assert session.scalar(select(func.count()).select_from(Purchase)) == 1
        assert session.scalar(select(func.count()).select_from(ShoppingItem)) == 0
    finally:
        session.close()

    # second checkout → nothing to buy
    assert (
        client.post("/api/shopping/checkout", headers=headers, json=None).status_code
        == 409
    )


def test_shopping_isolation_between_users(client, auth_headers):
    headers_a, _ = auth_headers(email="shop5a@example.com")
    headers_b, _ = auth_headers(email="shop5b@example.com")
    item = client.post(
        "/api/shopping", headers=headers_a, json={"name": "Curd", "quantity": 200, "unit": "g"}
    ).json()

    assert client.get("/api/shopping", headers=headers_b).json() == []
    assert (
        client.delete(f"/api/shopping/{item['id']}", headers=headers_b).status_code
        == 404
    )
