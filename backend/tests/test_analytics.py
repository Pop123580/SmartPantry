"""Honest analytics: unknown money is null, known money is exact."""

from datetime import UTC, datetime, timedelta


def _in(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


class TestEmptyStateIsAllUnknown:
    def test_fresh_user_gets_zeros_and_nulls(self, client, auth_headers):
        headers, _ = auth_headers(email="an1@example.com")
        body = client.get("/api/analytics/summary", headers=headers).json()

        # legacy fields still present for the existing frontend
        for key in (
            "totalPantryItems", "expiringSoon", "runningLow", "highRisk",
            "consumedLast30dEvents", "consumedLast30dQuantity",
            "wasteLogs", "wasteEstimatedValue",
        ):
            assert key in body, key

        assert body["totalPantryItems"] == 0
        assert body["atRiskItems"] == 0
        assert body["atRiskKnownValue"] is None          # nothing → unknown
        assert body["atRiskValueUnavailableCount"] == 0
        assert body["totalPurchaseValue"] is None
        assert body["knownValueSaved"] is None
        assert body["recentConsumption"] == []
        assert body["recentWaste"] == []
        assert body["recentPurchases"] == []
        assert body["currency"] == "INR"


class TestMoneyHonesty:
    def test_at_risk_without_prices_reports_items_not_rupees(
        self, client, auth_headers
    ):
        headers, _ = auth_headers(email="an2@example.com")
        client.post(
            "/api/pantry",
            headers=headers,
            json={"name": "Spinach", "quantity": 250, "unit": "g",
                  "expiresAt": _in(1)},  # expiring soon, no price
        )
        body = client.get("/api/analytics/summary", headers=headers).json()
        assert body["atRiskItems"] == 1
        assert body["atRiskKnownValue"] is None          # NOT a fake estimate
        assert body["atRiskValueUnavailableCount"] == 1

    def test_at_risk_with_price_reports_real_value(self, client, auth_headers):
        headers, _ = auth_headers(email="an3@example.com")
        client.post(
            "/api/pantry",
            headers=headers,
            json={"name": "Paneer", "quantity": 2, "unit": "pack",
                  "expiresAt": _in(1), "purchasePrice": 90, "currency": "INR"},
        )
        body = client.get("/api/analytics/summary", headers=headers).json()
        assert body["atRiskKnownValue"] == 180           # 2 × ₹90 — real data
        assert body["atRiskValueUnavailableCount"] == 0

    def test_value_saved_only_when_real_price_exists(self, client, auth_headers):
        headers, _ = auth_headers(email="an4@example.com")
        # buy with price → pantry gets stock + unit price
        client.post(
            "/api/shopping",
            headers=headers,
            json={"name": "Tomato", "quantity": 2, "unit": "kg",
                  "unitPrice": 40, "currency": "INR"},
        )
        assert client.post("/api/shopping/checkout", headers=headers).status_code == 200

        # nothing consumed yet
        body = client.get("/api/analytics/summary", headers=headers).json()
        assert body["totalPurchaseValue"] == 80
        assert body["knownValueSaved"] is None

        # cook exactly the tomatoes (0.3 kg recipe portion) via a crafted recipe
        recipes = client.get("/api/recipes/recommended", headers=headers).json()
        tomato_recipe = next(
            r for r in recipes
            if any("tomato" in i["name"].lower() for i in r["ingredients"])
        )
        client.post(f"/api/recipes/{tomato_recipe['id']}/cook", headers=headers)

        body = client.get("/api/analytics/summary", headers=headers).json()
        assert body["knownValueSaved"] is not None
        assert body["knownValueSaved"] > 0
        assert len(body["recentConsumption"]) >= 1
        assert body["recentConsumption"][0]["name"] is not None

    def test_recent_purchases_and_waste_feeds(self, client, auth_headers):
        headers, _ = auth_headers(email="an5@example.com")
        client.post(
            "/api/pantry", headers=headers,
            json={"name": "Curd", "quantity": 500, "unit": "g",
                  "purchasePrice": 30, "currency": "INR"},
        )
        state = client.get("/api/pantry", headers=headers).json()
        item_id = state[0]["id"]
        client.delete(f"/api/pantry/{item_id}?reason=spoiled", headers=headers)

        body = client.get("/api/analytics/summary", headers=headers).json()
        assert body["wasteLogs"] == 1
        assert body["wasteQuantity"] == 500
        # value derived from the REAL ₹30/pack…er g price recorded by the user
        assert body["wasteEstimatedValue"] == 500 * 30 / 1
        assert body["recentWaste"][0]["name"] == "Curd"
        assert body["recentWaste"][0]["reason"] == "spoiled"
