from app.models.user import User


def test_register_ignores_role_field(client):
    response = client.post(
        "/auth/register",
        json={"email": "hacker@example.com", "password": "pass12345", "full_name": "Hacker", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "staff"


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass12345", "full_name": "Dup"}
    assert client.post("/auth/register", json=payload).status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_success(client):
    client.post("/auth/register", json={"email": "user@example.com", "password": "pass12345", "full_name": "User"})
    response = client.post("/auth/login", data={"username": "user@example.com", "password": "pass12345"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(
        "/auth/register", json={"email": "user2@example.com", "password": "pass12345", "full_name": "User"}
    )
    response = client.post("/auth/login", data={"username": "user2@example.com", "password": "wrongpass"})
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post("/auth/login", data={"username": "nobody@example.com", "password": "pass12345"})
    assert response.status_code == 401


def test_login_inactive_user(client, db_session):
    client.post(
        "/auth/register",
        json={"email": "inactive@example.com", "password": "pass12345", "full_name": "Inactive"},
    )
    user = db_session.query(User).filter_by(email="inactive@example.com").one()
    user.is_active = False
    db_session.flush()
    response = client.post("/auth/login", data={"username": "inactive@example.com", "password": "pass12345"})
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client):
    client.post("/auth/register", json={"email": "me@example.com", "password": "pass12345", "full_name": "Me"})
    login = client.post("/auth/login", data={"username": "me@example.com", "password": "pass12345"})
    token = login.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
