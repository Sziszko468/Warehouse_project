"""Product-specific behavior not already covered by the generic suite in
test_master_data_crud.py: FK validation (category/supplier existence and soft-delete rejection),
price/threshold bounds, and search/filter combinations.
"""

from app.messages import Messages
from tests.constants import SAMPLE_UNIT_PRICE


def _make_product(client, admin_headers, category_id, **overrides):
    payload = {
        "sku": "SKU-DEFAULT",
        "name": "Default Product",
        "category_id": category_id,
        "unit_price": SAMPLE_UNIT_PRICE,
    }
    payload.update(overrides)
    return client.post("/products", json=payload, headers=admin_headers).json()


def test_create_product_with_missing_category_404(client, admin_headers):
    payload = {"sku": "SKU-300", "name": "Ethernet Cable", "category_id": 999999, "unit_price": SAMPLE_UNIT_PRICE}
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CATEGORY_NOT_FOUND


def test_create_product_with_missing_supplier_404(client, admin_headers, category_id):
    payload = {
        "sku": "SKU-301",
        "name": "Ethernet Cable",
        "category_id": category_id,
        "supplier_id": 999999,
        "unit_price": SAMPLE_UNIT_PRICE,
    }
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.SUPPLIER_NOT_FOUND


def test_create_product_negative_price_rejected(client, admin_headers, category_id):
    payload = {"sku": "SKU-400", "name": "Bad Product", "category_id": category_id, "unit_price": "-1.00"}
    assert client.post("/products", json=payload, headers=admin_headers).status_code == 422


def test_create_product_negative_threshold_rejected(client, admin_headers, category_id):
    payload = {
        "sku": "SKU-401",
        "name": "Bad Product 2",
        "category_id": category_id,
        "unit_price": SAMPLE_UNIT_PRICE,
        "min_stock_threshold": -1,
    }
    assert client.post("/products", json=payload, headers=admin_headers).status_code == 422


def test_create_product_zero_price_allowed(client, admin_headers, category_id):
    payload = {"sku": "SKU-402", "name": "Free Sample", "category_id": category_id, "unit_price": "0.00"}
    assert client.post("/products", json=payload, headers=admin_headers).status_code == 201


def test_create_product_with_soft_deleted_category_rejected(client, admin_headers, category_id):
    assert client.delete(f"/categories/{category_id}", headers=admin_headers).status_code == 204
    payload = {
        "sku": "SKU-500",
        "name": "Orphan Product",
        "category_id": category_id,
        "unit_price": SAMPLE_UNIT_PRICE,
    }
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CATEGORY_NOT_FOUND


def test_create_product_with_soft_deleted_supplier_rejected(client, admin_headers, category_id, supplier_id):
    assert client.delete(f"/suppliers/{supplier_id}", headers=admin_headers).status_code == 204
    payload = {
        "sku": "SKU-501",
        "name": "Orphan Product 2",
        "category_id": category_id,
        "supplier_id": supplier_id,
        "unit_price": SAMPLE_UNIT_PRICE,
    }
    response = client.post("/products", json=payload, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.SUPPLIER_NOT_FOUND


def test_update_product_to_missing_category_404(client, admin_headers, category_id):
    product = _make_product(client, admin_headers, category_id, sku="SKU-600")
    response = client.patch(f"/products/{product['id']}", json={"category_id": 999999}, headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CATEGORY_NOT_FOUND


def test_update_product_to_soft_deleted_category_404(client, admin_headers, category_id, other_category_id):
    product = _make_product(client, admin_headers, category_id, sku="SKU-601")
    assert client.delete(f"/categories/{other_category_id}", headers=admin_headers).status_code == 204
    response = client.patch(
        f"/products/{product['id']}", json={"category_id": other_category_id}, headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CATEGORY_NOT_FOUND


def test_search_by_name(client, admin_headers, category_id):
    _make_product(client, admin_headers, category_id, sku="SKU-700", name="Wireless Mouse")
    _make_product(client, admin_headers, category_id, sku="SKU-701", name="USB Keyboard")
    items = client.get("/products?search=Mouse", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Wireless Mouse"


def test_search_by_sku(client, admin_headers, category_id):
    _make_product(client, admin_headers, category_id, sku="ABC-123", name="Widget A")
    _make_product(client, admin_headers, category_id, sku="XYZ-999", name="Widget B")
    items = client.get("/products?search=ABC", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "ABC-123"


def test_search_case_insensitive(client, admin_headers, category_id):
    _make_product(client, admin_headers, category_id, sku="SKU-702", name="Wireless Mouse")
    items = client.get("/products?search=wireless", headers=admin_headers).json()["items"]
    assert len(items) == 1


def test_search_no_results(client, admin_headers, category_id):
    _make_product(client, admin_headers, category_id, sku="SKU-999")
    items = client.get("/products?search=NoSuchProductXYZ", headers=admin_headers).json()["items"]
    assert items == []


def test_filter_by_category_id(client, admin_headers, category_id, other_category_id):
    _make_product(client, admin_headers, category_id, sku="SKU-800")
    _make_product(client, admin_headers, other_category_id, sku="SKU-801")
    items = client.get(f"/products?category_id={category_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["category_id"] == category_id


def test_filter_by_supplier_id(client, admin_headers, category_id, supplier_id):
    _make_product(client, admin_headers, category_id, sku="SKU-900", supplier_id=supplier_id)
    _make_product(client, admin_headers, category_id, sku="SKU-901")
    items = client.get(f"/products?supplier_id={supplier_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "SKU-900"


def test_filter_combined_category_and_search(client, admin_headers, category_id, other_category_id):
    _make_product(client, admin_headers, category_id, sku="SKU-A1", name="Blue Widget")
    _make_product(client, admin_headers, category_id, sku="SKU-A2", name="Red Widget")
    _make_product(client, admin_headers, other_category_id, sku="SKU-B1", name="Blue Gadget")
    items = client.get(f"/products?category_id={category_id}&search=Blue", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "SKU-A1"
