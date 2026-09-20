"""End-to-end demo of the SmartPantry story against a RUNNING API:

    signup → add groceries → risk engine → recommended recipes
    → cook → inventory decreases + consumption recorded
    → shopping (inventory-aware) → checkout → back in the pantry

Usage:
    python scripts/demo_flow.py [--base http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta

import httpx


def iso_in(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def show(title: str, payload) -> None:
    print(f"\n── {title} ──")
    print(json.dumps(payload, indent=2, default=str)[:1200])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    stamp = datetime.now().strftime("%H%M%S")

    with httpx.Client(base_url=base, timeout=30) as api:
        # 1 ── signup (JWT comes straight back)
        r = api.post(
            "/api/auth/register",
            json={
                "name": "Ajay",
                "email": f"ajay.demo.{stamp}@example.com",
                "password": "password123",
            },
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        show("1. Signed up (JWT issued)", {"user": r.json()["user"]})

        # 2 ── add groceries
        groceries = [
            {"name": "Spinach", "quantity": 250, "unit": "g",
             "category": "Vegetables", "expiresAt": iso_in(1)},
            {"name": "Tomato", "quantity": 300, "unit": "g",
             "category": "Vegetables", "expiresAt": iso_in(2)},
            {"name": "Milk", "quantity": 0.2, "unit": "l",
             "category": "Dairy", "expiresAt": iso_in(6)},
            {"name": "Rice", "quantity": 2, "unit": "kg",
             "category": "Pantry Staples"},
        ]
        for g in groceries:
            api.post("/api/pantry", json=g, headers=headers).raise_for_status()

        # 3 ── risk engine verdicts
        pantry = api.get("/api/pantry", headers=headers).json()
        show(
            "3. Pantry with risk verdicts",
            [{k: i[k] for k in ("name", "quantity", "unit", "status", "risk", "expiresAt")}
             for i in pantry],
        )

        # 4-5 ── food rescue recommendations (Bedrock when configured)
        recipes = api.get("/api/recipes/recommended", headers=headers).json()
        show(
            "4/5. Recommended recipes (urgent items first)",
            [
                {
                    "name": r["name"],
                    "ingredients": r["ingredients"],
                    "reasoning": r["reasoning"],
                }
                for r in recipes
            ],
        )
        assert recipes, "expected at least one recipe"

        # 6-8 ── cook → inventory decreases, consumption recorded
        recipe = recipes[0]
        cooked = api.post(
            f"/api/recipes/{recipe['id']}/cook", headers=headers
        )
        cooked.raise_for_status()
        show(
            f"6-8. Cooked '{recipe['name']}' — stock deducted",
            cooked.json()["consumed"],
        )
        pantry_after = api.get("/api/pantry", headers=headers).json()
        show(
            "    Pantry after cooking",
            [{k: i[k] for k in ("name", "quantity", "unit", "status", "risk")} for i in pantry_after],
        )

        # 9 ── shopping checks inventory (realistic real prices per unit)
        api.post("/api/shopping", json={"name": "Spinach", "quantity": 250, "unit": "g",
                                        "unitPrice": 0.14, "currency": "INR"},   # ₹35 per 250 g
                 headers=headers).raise_for_status()
        api.post("/api/shopping", json={"name": "Tomato", "quantity": 1, "unit": "kg",
                                        "unitPrice": 40, "currency": "INR"},     # ₹40 per kg
                 headers=headers).raise_for_status()
        api.post("/api/shopping", json={"name": "Paneer", "quantity": 200, "unit": "g",
                                        "unitPrice": 0.5, "currency": "INR"},    # ₹100 per 200 g
                 headers=headers).raise_for_status()
        shopping = api.get("/api/shopping", headers=headers).json()
        show(
            "9. Shopping list (inventory-aware)",
            [{k: i[k] for k in ("name", "reason", "inInventory")} for i in shopping],
        )

        # 10-11 ── checkout → purchase + merged pantry
        result = api.post("/api/shopping/checkout", headers=headers, json=None)
        result.raise_for_status()
        show("10/11. Checkout result", result.json())
        pantry_final = api.get("/api/pantry", headers=headers).json()
        show(
            "    Final pantry",
            [{k: i[k] for k in ("name", "quantity", "unit", "status", "risk")} for i in pantry_final],
        )

        # 12 ── purchase history (Purchase + PurchaseItems, real prices)
        purchases = api.get("/api/purchases", headers=headers).json()
        show("12. Purchase history", purchases)
        detail = api.get(f"/api/purchases/{purchases[0]['id']}", headers=headers).json()
        show("    Purchase detail (line items)", detail["items"])

        # 13 ── analytics (honest money: prices recorded for 3 items)
        summary = api.get("/api/analytics/summary", headers=headers).json()
        show("13. Analytics summary (real values only)", summary)

    print("\n✅ Full SmartPantry demo flow completed successfully.")


if __name__ == "__main__":
    main()
