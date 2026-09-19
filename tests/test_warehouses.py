def test_staff_can_read_warehouses(client, staff_headers):
    assert client.get("/warehouses", headers=staff_headers).status_code == 200


def test_staff_cannot_write_warehouses(client, staff_headers):
    assert client.post("/warehouses", json={"name": "Main"}, headers=staff_headers).status_code == 403


def test_admin_warehouse_crud_roundtrip(client, admin_headers):
    create = client.post(
        "/warehouses", json={"name": "Main Warehouse", "address": "1 Depot Rd"}, headers=admin_headers
    )
    assert create.status_code == 201
    warehouse = create.json()

    update = client.patch(f"/warehouses/{warehouse['id']}", json={"address": "2 Depot Rd"}, headers=admin_headers)
    assert update.status_code == 200
    assert update.json()["address"] == "2 Depot Rd"

    delete = client.delete(f"/warehouses/{warehouse['id']}", headers=admin_headers)
    assert delete.status_code == 204

    list_default = client.get("/warehouses", headers=admin_headers).json()
    assert all(w["id"] != warehouse["id"] for w in list_default["items"])


def test_duplicate_warehouse_name(client, admin_headers):
    client.post("/warehouses", json={"name": "North Hub"}, headers=admin_headers)
    dup = client.post("/warehouses", json={"name": "North Hub"}, headers=admin_headers)
    assert dup.status_code == 409
