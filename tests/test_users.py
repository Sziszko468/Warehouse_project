from app.models.user import User, UserRole
from app.security import hash_password


def test_staff_cannot_list_users(client, staff_headers):
    assert client.get("/users", headers=staff_headers).status_code == 403


def test_admin_can_promote_staff_to_admin(client, admin_headers, staff_user):
    response = client.patch(f"/users/{staff_user.id}", json={"role": "admin"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_cannot_demote_last_admin(client, admin_headers, admin_user):
    response = client.patch(f"/users/{admin_user.id}", json={"role": "staff"}, headers=admin_headers)
    assert response.status_code == 409


def test_cannot_deactivate_last_admin(client, admin_headers, admin_user):
    response = client.patch(f"/users/{admin_user.id}", json={"is_active": False}, headers=admin_headers)
    assert response.status_code == 409


def test_can_demote_admin_when_another_admin_exists(client, admin_headers, admin_user, db_session):
    other_admin = User(
        email="other-admin@example.com",
        hashed_password=hash_password("pass12345"),
        full_name="Other Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(other_admin)
    db_session.flush()

    response = client.patch(f"/users/{admin_user.id}", json={"role": "staff"}, headers=admin_headers)
    assert response.status_code == 200


def test_user_not_found(client, admin_headers):
    assert client.get("/users/999", headers=admin_headers).status_code == 404
