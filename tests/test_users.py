import pytest

from app.messages import Messages
from app.models.user import User, UserRole
from app.security import hash_password
from tests.constants import PAGE_LIMIT_MAX, SAMPLE_PASSWORD


def _create_extra_admin(db_session, email: str = "other-admin@example.com") -> User:
    user = User(
        email=email, hashed_password=hash_password(SAMPLE_PASSWORD), full_name="Other Admin", role=UserRole.ADMIN
    )
    db_session.add(user)
    db_session.flush()
    return user


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


def test_unauthenticated_rejected_on_list(client):
    assert client.get("/users").status_code == 401


def test_unauthenticated_rejected_on_get(client):
    assert client.get("/users/1").status_code == 401


def test_unauthenticated_rejected_on_update(client):
    assert client.patch("/users/1", json={}).status_code == 401


def test_staff_cannot_list_users(client, staff_headers):
    assert client.get("/users", headers=staff_headers).status_code == 403


def test_staff_cannot_get_user(client, staff_headers, staff_user):
    assert client.get(f"/users/{staff_user.id}", headers=staff_headers).status_code == 403


def test_staff_cannot_update_user(client, staff_headers, staff_user):
    assert (
        client.patch(f"/users/{staff_user.id}", json={"full_name": "New Name"}, headers=staff_headers).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


def test_user_not_found(client, admin_headers):
    response = client.get("/users/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.USER_NOT_FOUND


def test_update_nonexistent_user_404(client, admin_headers):
    response = client.patch("/users/999999", json={"full_name": "Ghost"}, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.USER_NOT_FOUND


def test_admin_can_get_own_profile(client, admin_headers, admin_user):
    response = client.get(f"/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


def test_updating_full_name_only_leaves_role_and_active_untouched(client, admin_headers, staff_user):
    response = client.patch(f"/users/{staff_user.id}", json={"full_name": "Renamed Staff"}, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Renamed Staff"
    assert body["role"] == "staff"
    assert body["is_active"] is True


def test_update_with_invalid_role_value_rejected(client, admin_headers, staff_user):
    response = client.patch(f"/users/{staff_user.id}", json={"role": "superuser"}, headers=admin_headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Role promotion / demotion and the last-admin guard
# ---------------------------------------------------------------------------


def test_admin_can_promote_staff_to_admin(client, admin_headers, staff_user):
    response = client.patch(f"/users/{staff_user.id}", json={"role": "admin"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_cannot_demote_last_admin(client, admin_headers, admin_user):
    response = client.patch(f"/users/{admin_user.id}", json={"role": "staff"}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == Messages.LAST_ADMIN_GUARD


def test_cannot_deactivate_last_admin(client, admin_headers, admin_user):
    response = client.patch(f"/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == Messages.LAST_ADMIN_GUARD


def test_can_demote_admin_when_another_admin_exists(client, admin_headers, admin_user, db_session):
    _create_extra_admin(db_session)
    response = client.patch(f"/users/{admin_user.id}", json={"role": "staff"}, headers=admin_headers)
    assert response.status_code == 200


def test_can_deactivate_admin_when_another_admin_exists(client, admin_headers, admin_user, db_session):
    _create_extra_admin(db_session)
    response = client.patch(f"/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 200


def test_demoting_staff_user_never_triggers_last_admin_guard(client, admin_headers, staff_user):
    # staff_user isn't an admin at all, so the guard must not even consider them
    response = client.patch(f"/users/{staff_user.id}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Listing: filters and pagination
# ---------------------------------------------------------------------------


def test_list_filter_by_role(client, admin_headers, staff_user):
    items = client.get("/users?role=staff", headers=admin_headers).json()["items"]
    assert all(item["role"] == "staff" for item in items)
    assert any(item["id"] == staff_user.id for item in items)


def test_list_filter_by_is_active(client, admin_headers, staff_user, db_session):
    staff_user.is_active = False
    db_session.flush()

    items = client.get("/users?is_active=false", headers=admin_headers).json()["items"]
    assert all(item["is_active"] is False for item in items)
    assert any(item["id"] == staff_user.id for item in items)


def test_list_pagination_limit_over_max_rejected(client, admin_headers):
    response = client.get(f"/users?limit={PAGE_LIMIT_MAX + 1}", headers=admin_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("bad_offset", [-1, -100])
def test_list_pagination_negative_offset_rejected(client, admin_headers, bad_offset):
    response = client.get(f"/users?offset={bad_offset}", headers=admin_headers)
    assert response.status_code == 422
