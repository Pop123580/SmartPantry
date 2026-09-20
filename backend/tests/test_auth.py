"""Auth: register, login, invalid password, protected routes."""


def test_register_returns_token_and_user(register_user):
    body = register_user(email="ajay@example.com", name="Ajay")
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["name"] == "Ajay"
    assert body["user"]["email"] == "ajay@example.com"
    assert body["user"]["id"]


def test_register_duplicate_email_rejected(client, register_user):
    register_user(email="ajay@example.com")
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Ajay Again",
            "email": "ajay@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 409


def test_register_short_password_is_422(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "A", "email": "a@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_login_success(client, register_user):
    register_user(email="ajay@example.com", name="Ajay")
    response = client.post(
        "/api/auth/login",
        json={"email": "ajay@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "ajay@example.com"


def test_login_wrong_password(client, register_user):
    register_user(email="ajay@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "ajay@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_me_with_and_without_token(client, auth_headers):
    headers, user = auth_headers(email="a@example.com", name="Ajay")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "a@example.com"
    assert response.json()["name"] == "Ajay"

    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token(client):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_protected_route_rejects_anonymous(client):
    assert client.get("/api/pantry").status_code == 401
    assert client.post("/api/pantry", json={}).status_code == 401
    assert client.get("/api/recipes/recommended").status_code == 401
    assert client.get("/api/shopping").status_code == 401


def test_logout(client, auth_headers):
    headers, _user = auth_headers(email="b@example.com")
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 200
    assert "message" in response.json()
