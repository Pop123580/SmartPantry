"""Cook flow edge cases (§10): FEFO batching, unit conversion,
zero-quantity items, partial stock, repeated cooking, access control."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.models import ConsumptionLog, PantryItem, Recipe, RecipeIngredient
from tests.conftest import TestingSessionLocal


def _mk_recipe(ingredients: list[tuple[str, float, str]], owner_id: str) -> str:
    """Craft a recipe straight in the DB so quantities are exact."""
    session = TestingSessionLocal()
    try:
        recipe = Recipe(
            owner_id=UUID(owner_id),
            name="Test Recipe",
            reasoning="Crafted for tests",
            instructions=["step 1", "step 2"],
            ingredients=[
                RecipeIngredient(name=n, quantity=q, unit=u)
                for n, q, u in ingredients
            ],
        )
        session.add(recipe)
        session.commit()
        return str(recipe.id)
    finally:
        session.close()


def _add_pantry(client, headers, name, qty, unit, expires_days=None):
    body = {"name": name, "quantity": qty, "unit": unit}
    if expires_days is not None:
        body["expiresAt"] = (
            datetime.now(UTC) + timedelta(days=expires_days)
        ).isoformat()
    return client.post("/api/pantry", headers=headers, json=body)


class TestUnitConversion:
    def test_recipe_in_grams_pantry_in_kg(self, client, auth_headers):
        headers, user = auth_headers(email="cook1@example.com")
        _add_pantry(client, headers, "Rice", 1, "kg")
        recipe_id = _mk_recipe([("Rice", 400, "g")], user["id"])

        assert client.post(
            f"/api/recipes/{recipe_id}/cook", headers=headers
        ).status_code == 200
        rice = client.get("/api/pantry", headers=headers).json()[0]
        assert rice["quantity"] == 0.6  # 1 kg − 400 g
        assert rice["unit"] == "kg"

    def test_recipe_in_kg_pantry_in_grams(self, client, auth_headers):
        headers, user = auth_headers(email="cook2@example.com")
        _add_pantry(client, headers, "Flour", 500, "g")
        recipe_id = _mk_recipe([("Flour", 0.3, "kg")], user["id"])

        assert client.post(
            f"/api/recipes/{recipe_id}/cook", headers=headers
        ).status_code == 200
        flour = client.get("/api/pantry", headers=headers).json()[0]
        assert flour["quantity"] == 200

    def test_incompatible_units_report_shortfall(self, client, auth_headers):
        headers, user = auth_headers(email="cook3@example.com")
        _add_pantry(client, headers, "Olive Oil", 500, "ml")
        recipe_id = _mk_recipe([("Olive Oil", 1, "kg")], user["id"])

        response = client.post(f"/api/recipes/{recipe_id}/cook", headers=headers)
        assert response.status_code == 409
        shortfalls = response.json()["detail"]["shortfalls"]
        assert shortfalls[0]["available"] == 0  # ml ≠ kg


class TestFEFOMultipleBatches:
    def test_soonest_expiring_batch_is_used_first(self, client, auth_headers):
        headers, user = auth_headers(email="cook4@example.com")
        expiring = _add_pantry(client, headers, "Milk", 1, "l", expires_days=1).json()
        later = _add_pantry(client, headers, "Milk", 1, "l", expires_days=10).json()
        recipe_id = _mk_recipe([("Milk", 1.5, "l")], user["id"])

        result = client.post(f"/api/recipes/{recipe_id}/cook", headers=headers)
        assert result.status_code == 200

        items = {i["id"]: i for i in client.get("/api/pantry", headers=headers).json()}
        assert items[expiring["id"]]["quantity"] == 0    # FEFO: this one first
        assert items[later["id"]]["quantity"] == 0.5     # remainder from here

        # two logs — one per batch
        session = TestingSessionLocal()
        try:
            logs = session.scalar(select(func.count()).select_from(ConsumptionLog))
            assert logs == 2
            negative = session.scalar(
                select(func.count())
                .select_from(PantryItem)
                .where(PantryItem.quantity < 0)
            )
            assert negative == 0
        finally:
            session.close()


class TestStockIntegrity:
    def test_zero_quantity_item_is_ignored(self, client, auth_headers):
        headers, user = auth_headers(email="cook5@example.com")
        _add_pantry(client, headers, "Spinach", 250, "g", expires_days=1)
        recipe_id = _mk_recipe([("Spinach", 250, "g")], user["id"])
        assert client.post(
            f"/api/recipes/{recipe_id}/cook", headers=headers
        ).status_code == 200  # drains the batch to exactly zero

        again = client.post(f"/api/recipes/{recipe_id}/cook", headers=headers)
        assert again.status_code == 409  # zero stock is not negative stock

    def test_partial_stock_cooks_nothing(self, client, auth_headers):
        headers, user = auth_headers(email="cook6@example.com")
        _add_pantry(client, headers, "Paneer", 100, "g")
        recipe_id = _mk_recipe([("Paneer", 200, "g")], user["id"])

        response = client.post(f"/api/recipes/{recipe_id}/cook", headers=headers)
        assert response.status_code == 409
        shortfall = response.json()["detail"]["shortfalls"][0]
        assert shortfall["needed"] == 200
        assert shortfall["available"] == 100
        # stock untouched — failed cook is a no-op
        paneer = client.get("/api/pantry", headers=headers).json()[0]
        assert paneer["quantity"] == 100

    def test_repeated_cooking_depletes_then_fails(self, client, auth_headers):
        headers, user = auth_headers(email="cook7@example.com")
        _add_pantry(client, headers, "Egg", 6, "pcs")
        recipe_id = _mk_recipe([("Egg", 2, "pcs")], user["id"])

        for _ in range(3):  # 6 → 4 → 2 → 0
            assert client.post(
                f"/api/recipes/{recipe_id}/cook", headers=headers
            ).status_code == 200
        fourth = client.post(f"/api/recipes/{recipe_id}/cook", headers=headers)
        assert fourth.status_code == 409
        eggs = client.get("/api/pantry", headers=headers).json()[0]
        assert eggs["quantity"] == 0
        assert eggs["status"] == "running_low"  # zero qty → running low


class TestAccessControl:
    def test_cannot_cook_another_users_private_recipe(
        self, client, auth_headers
    ):
        headers_a, user_a = auth_headers(email="cook8a@example.com")
        headers_b, _ = auth_headers(email="cook8b@example.com")
        _add_pantry(client, headers_b, "Spinach", 500, "g", expires_days=1)
        recipe_id = _mk_recipe([("Spinach", 100, "g")], user_a["id"])

        assert (
            client.get(f"/api/recipes/{recipe_id}", headers=headers_b).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/recipes/{recipe_id}/cook", headers=headers_b
            ).status_code
            == 404
        )

    def test_unknown_uuid_recipe_is_404_not_500(self, client, auth_headers):
        headers, _ = auth_headers(email="cook9@example.com")
        assert (
            client.post(f"/api/recipes/{uuid4()}/cook", headers=headers).status_code
            == 404
        )
