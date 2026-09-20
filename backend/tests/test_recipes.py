"""Recipes: recommendation, detail, cooking and inventory deduction."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import ConsumptionLog, PantryItem
from tests.conftest import TestingSessionLocal


def _days_from_now(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def _seed_pantry(client, headers):
    client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Spinach", "quantity": 250, "unit": "g",
            "category": "Vegetables", "expiresAt": _days_from_now(1),
        },
    )
    client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Tomato", "quantity": 300, "unit": "g",
            "category": "Vegetables", "expiresAt": _days_from_now(2),
        },
    )
    client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Rice", "quantity": 2000, "unit": "g",
            "category": "Pantry Staples",
        },
    )


def test_recommended_prioritises_urgent_items(client, auth_headers):
    headers, _user = auth_headers(email="recipes1@example.com")
    _seed_pantry(client, headers)

    response = client.get("/api/recipes/recommended", headers=headers)
    assert response.status_code == 200, response.text
    recipes = response.json()
    assert len(recipes) >= 1

    recipe = recipes[0]
    assert set(recipe) >= {"id", "name", "ingredients", "reasoning", "imageUrl"}
    ingredient_names = [i["name"].lower() for i in recipe["ingredients"]]
    assert any("spinach" in name for name in ingredient_names)
    for ingredient in recipe["ingredients"]:
        assert set(ingredient) == {"name", "quantity", "unit"}
        assert ingredient["quantity"] > 0
    assert recipe["reasoning"]


def test_recommended_empty_pantry_returns_empty_list(client, auth_headers):
    headers, _user = auth_headers(email="recipes2@example.com")
    response = client.get("/api/recipes/recommended", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_recipe_detail(client, auth_headers):
    headers, _user = auth_headers(email="recipes3@example.com")
    _seed_pantry(client, headers)
    recipes = client.get("/api/recipes/recommended", headers=headers).json()
    recipe_id = recipes[0]["id"]

    detail = client.get(f"/api/recipes/{recipe_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == recipe_id
    assert isinstance(detail.json()["instructions"], list)
    assert len(detail.json()["instructions"]) >= 2


def test_recipe_detail_not_found(client, auth_headers):
    headers, _user = auth_headers(email="recipes4@example.com")
    response = client.get(
        "/api/recipes/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


def test_cook_deducts_inventory_and_logs_consumption(client, auth_headers):
    headers, user = auth_headers(email="recipes5@example.com")
    _seed_pantry(client, headers)
    recipes = client.get("/api/recipes/recommended", headers=headers).json()
    recipe = recipes[0]
    spinach_qty = next(
        i["quantity"] for i in recipe["ingredients"] if "spinach" in i["name"].lower()
    )

    cooked = client.post(f"/api/recipes/{recipe['id']}/cook", headers=headers)
    assert cooked.status_code == 200, cooked.text
    result = cooked.json()
    assert set(result) >= {"recipeId", "cookedAt", "consumed", "updatedPantry"}
    assert result["consumed"]

    # Pantry reflects the deduction (spinach portion fully used: 250g)
    pantry = client.get("/api/pantry", headers=headers).json()
    spinach = next(i for i in pantry if i["name"].lower() == "spinach")
    assert spinach["quantity"] == 250 - spinach_qty
    assert spinach["quantity"] >= 0  # NEVER negative
    rice = next(i for i in pantry if i["name"].lower() == "rice")
    assert rice["quantity"] == 2000 - 300  # 300 g portion cooked

    # Consumption logs were written
    session = TestingSessionLocal()
    try:
        logs = session.scalar(select(func.count()).select_from(ConsumptionLog))
        assert logs == len(result["consumed"])
        negative = session.scalar(
            select(func.count()).select_from(PantryItem).where(PantryItem.quantity < 0)
        )
        assert negative == 0
    finally:
        session.close()

    # Cooking again with the same recipe must fail cleanly: spinach is gone
    again = client.post(f"/api/recipes/{recipe['id']}/cook", headers=headers)
    assert again.status_code == 409
    detail = again.json()["detail"]
    assert detail["shortfalls"]
    assert any("spinach" in s["name"].lower() for s in detail["shortfalls"])


def test_cook_unknown_recipe_is_404(client, auth_headers):
    headers, _user = auth_headers(email="recipes6@example.com")
    response = client.post(
        "/api/recipes/00000000-0000-0000-0000-000000000000/cook", headers=headers
    )
    assert response.status_code == 404
