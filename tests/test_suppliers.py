def test_staff_can_read_suppliers(client, staff_headers):
    assert client.get("/suppliers", headers=staff_headers).status_code == 200


def test_staff_cannot_write_suppliers(client, staff_headers):
    assert client.post("/suppliers", json={"name": "Acme Corp"}, headers=staff_headers).status_code == 403


def test_admin_supplier_crud_roundtrip(client, admin_headers):
    create = client.post(
        "/suppliers", json={"name": "Acme Corp", "email": "sales@acme.example"}, headers=admin_headers
    )
    assert create.status_code == 201
    supplier = create.json()

    update = client.patch(f"/suppliers/{supplier['id']}", json={"phone": "555-1234"}, headers=admin_headers)
    assert update.status_code == 200
    assert update.json()["phone"] == "555-1234"

    delete = client.delete(f"/suppliers/{supplier['id']}", headers=admin_headers)
    assert delete.status_code == 204

    list_default = client.get("/suppliers", headers=admin_headers).json()
    assert all(s["id"] != supplier["id"] for s in list_default["items"])


def test_supplier_names_need_not_be_unique(client, admin_headers):
    first = client.post("/suppliers", json={"name": "Acme Corp"}, headers=admin_headers)
    second = client.post("/suppliers", json={"name": "Acme Corp"}, headers=admin_headers)
    assert first.status_code == 201
    assert second.status_code == 201
