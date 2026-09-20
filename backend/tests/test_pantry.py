"""Pantry CRUD + ownership isolation + exact response contract."""

from datetime import UTC, datetime, timedelta

PANTRY_KEYS = {
    "id", "name", "quantity", "unit", "category",
    "status", "risk", "expiresAt", "imageUrl",
}


def _days_from_now(days: float) -> str:
    return (datetime.now(UTC) + timedelta(days=days)).isoformat()


def test_create_item_contract(client, auth_headers):
    headers, _user = auth_headers(email="pantry1@example.com")
    response = client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Rice",
            "quantity": 500,
            "unit": "g",
            "category": "Pantry Staples",
            "expiresAt": _days_from_now(365),
            "imageUrl": None,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert set(body) == PANTRY_KEYS
    assert body["name"] == "Rice"
    assert body["quantity"] == 500
    assert body["unit"] == "g"
    assert body["category"] == "Pantry Staples"
    assert body["status"] == "safe"
    assert body["risk"] == "low"
    assert body["expiresAt"].endswith("Z")
    assert body["imageUrl"] is None


def test_create_defaults_and_validation(client, auth_headers):
    headers, _user = auth_headers(email="pantry2@example.com")
    response = client.post(
        "/api/pantry", headers=headers, json={"name": "Spinach", "quantity": 250}
    )
    assert response.status_code == 201
    assert response.json()["unit"] == "pcs"

    bad = client.post(
        "/api/pantry", headers=headers, json={"name": "X", "quantity": -3}
    )
    assert bad.status_code == 422


def test_list_get_patch_delete(client, auth_headers):
    headers, _user = auth_headers(email="pantry3@example.com")
    created = client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Tomato",
            "quantity": 300,
            "unit": "g",
            "expiresAt": _days_from_now(6),
        },
    )
    item_id = created.json()["id"]

    listed = client.get("/api/pantry", headers=headers)
    assert listed.status_code == 200
    assert [i["id"] for i in listed.json()] == [item_id]

    fetched = client.get(f"/api/pantry/{item_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Tomato"

    patched = client.patch(
        f"/api/pantry/{item_id}", headers=headers, json={"quantity": 150}
    )
    assert patched.status_code == 200
    assert patched.json()["quantity"] == 150

    deleted = client.delete(f"/api/pantry/{item_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/pantry/{item_id}", headers=headers).status_code == 404


def test_delete_with_reason_writes_waste_log(client, auth_headers):
    headers, _user = auth_headers(email="pantry4@example.com")
    created = client.post(
        "/api/pantry",
        headers=headers,
        json={"name": "Milk", "quantity": 1, "unit": "l"},
    )
    item_id = created.json()["id"]
    deleted = client.delete(
        f"/api/pantry/{item_id}?reason=expired&value=60", headers=headers
    )
    assert deleted.status_code == 204

    summary = client.get("/api/analytics/summary", headers=headers).json()
    assert summary["wasteLogs"] == 1
    assert summary["wasteEstimatedValue"] == 60


# ── ownership: user B can never see/touch user A's items ─────────────


def test_ownership_isolation(client, auth_headers):
    headers_a, _ = auth_headers(email="owner-a@example.com")
    headers_b, _ = auth_headers(email="user-b@example.com")

    created = client.post(
        "/api/pantry",
        headers=headers_a,
        json={"name": "Paneer", "quantity": 200, "unit": "g"},
    )
    item_id = created.json()["id"]

    # B's list is empty; every direct access by B → 404 (never 403 w/ data)
    assert client.get("/api/pantry", headers=headers_b).json() == []
    assert client.get(f"/api/pantry/{item_id}", headers=headers_b).status_code == 404
    assert (
        client.patch(
            f"/api/pantry/{item_id}", headers=headers_b, json={"quantity": 1}
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/pantry/{item_id}", headers=headers_b).status_code == 404
    )
    # A's item is untouched
    assert client.get(
        f"/api/pantry/{item_id}", headers=headers_a
    ).json()["quantity"] == 200


def test_expiring_spinach_is_flagged(client, auth_headers):
    """The spec's headline example end-to-end through the API."""
    headers, _user = auth_headers(email="pantry5@example.com")
    created = client.post(
        "/api/pantry",
        headers=headers,
        json={
            "name": "Spinach",
            "quantity": 250,
            "unit": "g",
            "category": "Vegetables",
            "expiresAt": _days_from_now(1),
        },
    )
    body = created.json()
    assert body["status"] == "expiring_soon"
    assert body["risk"] == "high"
