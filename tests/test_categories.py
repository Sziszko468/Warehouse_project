def test_staff_can_read_categories(client, staff_headers):
    response = client.get("/categories", headers=staff_headers)
    assert response.status_code == 200


def test_staff_cannot_write_categories(client, staff_headers):
    assert client.post("/categories", json={"name": "Cables"}, headers=staff_headers).status_code == 403
    assert client.patch("/categories/1", json={"name": "X"}, headers=staff_headers).status_code == 403
    assert client.delete("/categories/1", headers=staff_headers).status_code == 403


def test_admin_category_crud_roundtrip(client, admin_headers):
    create = client.post(
        "/categories", json={"name": "Cables", "description": "All cable types"}, headers=admin_headers
    )
    assert create.status_code == 201
    category = create.json()
    assert category["name"] == "Cables"
    assert category["is_active"] is True

    get_resp = client.get(f"/categories/{category['id']}", headers=admin_headers)
    assert get_resp.status_code == 200

    update = client.patch(f"/categories/{category['id']}", json={"description": "Updated"}, headers=admin_headers)
    assert update.status_code == 200
    assert update.json()["description"] == "Updated"

    delete = client.delete(f"/categories/{category['id']}", headers=admin_headers)
    assert delete.status_code == 204

    list_default = client.get("/categories", headers=admin_headers).json()
    assert all(c["id"] != category["id"] for c in list_default["items"])

    list_all = client.get("/categories?include_inactive=true", headers=admin_headers).json()
    assert any(c["id"] == category["id"] for c in list_all["items"])


def test_duplicate_category_name(client, admin_headers):
    client.post("/categories", json={"name": "Monitors"}, headers=admin_headers)
    dup = client.post("/categories", json={"name": "Monitors"}, headers=admin_headers)
    assert dup.status_code == 409


def test_category_not_found(client, admin_headers):
    assert client.get("/categories/999", headers=admin_headers).status_code == 404
