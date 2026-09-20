from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.messages import Messages
from app.models.user import User
from app.security import JWT_ALGORITHM
from tests.constants import SAMPLE_PASSWORD


def _register(client, email: str, password: str = SAMPLE_PASSWORD, full_name: str = "Test User"):
    return client.post("/auth/register", json={"email": email, "password": password, "full_name": full_name})


def _login(client, email: str, password: str = SAMPLE_PASSWORD):
    return client.post("/auth/login", data={"username": email, "password": password})


def _token_with_payload(payload: dict, secret: str = settings.secret_key) -> str:
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_ignores_role_field(client):
    response = client.post(
        "/auth/register",
        json={"email": "hacker@example.com", "password": SAMPLE_PASSWORD, "full_name": "Hacker", "role": "admin"},
    )
    assert response.status_code == 201
    assert response.json()["role"] == "staff"


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": SAMPLE_PASSWORD, "full_name": "Dup"}
    assert client.post("/auth/register", json=payload).status_code == 201
    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["detail"] == Messages.EMAIL_ALREADY_REGISTERED


def test_register_new_account_defaults_to_active(client, db_session):
    _register(client, "fresh@example.com")
    user = db_session.query(User).filter_by(email="fresh@example.com").one()
    assert user.is_active is True


@pytest.mark.parametrize("missing_field", ["email", "password", "full_name"])
def test_register_missing_required_field_rejected(client, missing_field):
    payload = {"email": "incomplete@example.com", "password": SAMPLE_PASSWORD, "full_name": "Incomplete"}
    del payload[missing_field]
    assert client.post("/auth/register", json=payload).status_code == 422


def test_register_invalid_email_format_rejected(client):
    payload = {"email": "not-an-email", "password": SAMPLE_PASSWORD, "full_name": "Bad Email"}
    assert client.post("/auth/register", json=payload).status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_success(client):
    _register(client, "user@example.com")
    response = _login(client, "user@example.com")
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    _register(client, "user2@example.com")
    response = _login(client, "user2@example.com", password="wrong-password")
    assert response.status_code == 401
    assert response.json()["detail"] == Messages.INCORRECT_CREDENTIALS


def test_login_unknown_email(client):
    response = _login(client, "nobody@example.com")
    assert response.status_code == 401
    assert response.json()["detail"] == Messages.INCORRECT_CREDENTIALS


def test_login_inactive_user(client, db_session):
    _register(client, "inactive@example.com")
    user = db_session.query(User).filter_by(email="inactive@example.com").one()
    user.is_active = False
    db_session.flush()
    response = _login(client, "inactive@example.com")
    assert response.status_code == 401


def test_login_missing_password_rejected(client):
    response = client.post("/auth/login", data={"username": "user@example.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /auth/me and token validation
# ---------------------------------------------------------------------------


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client):
    _register(client, "me@example.com")
    token = _login(client, "me@example.com").json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_me_rejects_malformed_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401
    assert response.json()["detail"] == Messages.COULD_NOT_VALIDATE_CREDENTIALS


def test_me_rejects_wrong_signature_token(client, admin_user):
    payload = {"sub": str(admin_user.id), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = _token_with_payload(payload, secret="a-completely-different-secret-value-32b")
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_rejects_expired_token(client, admin_user):
    payload = {"sub": str(admin_user.id), "exp": datetime.now(UTC) - timedelta(minutes=1)}
    token = _token_with_payload(payload)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_rejects_token_without_sub_claim(client):
    payload = {"exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = _token_with_payload(payload)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_me_rejects_missing_bearer_prefix(client):
    _register(client, "noprefix@example.com")
    token = _login(client, "noprefix@example.com").json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": token})
    assert response.status_code == 401


def test_me_rejects_token_for_deleted_user_id(client):
    payload = {"sub": "999999", "exp": datetime.now(UTC) + timedelta(minutes=5)}
    token = _token_with_payload(payload)
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
