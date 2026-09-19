import pytest


@pytest.fixture
def category_id(client, admin_headers) -> int:
    response = client.post("/categories", json={"name": "Cables"}, headers=admin_headers)
    return response.json()["id"]


def test_staff_can_read_products(client, staff_headers):
    assert client.get("/products", headers=staff_headers).status_code == 200


def test_staff_cannot_write_products(client, staff_headers, category_id):
    payload = {"sku": "SKU-1", "name": "USB Cable", "category_id": category_id, "unit_price": "4.99"}
    assert client.post("/products", json=payload, headers=staff_headers).status_code == 403


def test_admin_product_crud_roundtrip(client, admin_headers, category_id):
    payload = {
        "sku": "SKU-100",
        "name": "USB-C Cable 1m",
        "category_id": category_id,
        "unit_price": "4.99",
        "min_stock_threshold": 10,
    }
    create = client.post("/products", json=payload, headers=admin_headers)
    assert create.status_code == 201
    product = create.json()
    assert product["sku"] == "SKU-100"

    update = client.patch(f"/products/{product['id']}", json={"unit_price": "5.49"}, headers=admin_headers)
    assert update.status_code == 200
    assert update.json()["unit_price"] == "5.49"

    delete = client.delete(f"/products/{product['id']}", headers=admin_headers)
    assert delete.status_code == 204

    list_default = client.get("/products", headers=admin_headers).json()
    assert all(p["id"] != product["id"] for p in list_default["items"])


def test_duplicate_sku(client, admin_headers, category_id):
    payload = {"sku": "SKU-200", "name": "HDMI Cable", "category_id": category_id, "unit_price": "9.99"}
    assert client.post("/products", json=payload, headers=admin_headers).status_code == 201
    dup = client.post("/products", json=payload, headers=admin_headers)
    assert dup.status_code == 409


def test_create_product_with_missing_category(client, admin_headers):
    payload = {"sku": "SKU-300", "name": "Ethernet Cable", "category_id": 999, "unit_price": "3.99"}
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 404


def test_create_product_negative_price_rejected(client, admin_headers, category_id):
    payload = {"sku": "SKU-400", "name": "Bad Product", "category_id": category_id, "unit_price": "-1.00"}
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 422
