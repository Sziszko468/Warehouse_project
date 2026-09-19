import pytest


@pytest.fixture
def category_id(client, admin_headers) -> int:
    return client.post("/categories", json={"name": "Cables"}, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_a_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse A"}, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_b_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse B"}, headers=admin_headers).json()["id"]


def _make_product(client, admin_headers, category_id, sku, threshold):
    payload = {
        "sku": sku,
        "name": sku,
        "category_id": category_id,
        "unit_price": "1.00",
        "min_stock_threshold": threshold,
    }
    return client.post("/products", json=payload, headers=admin_headers).json()["id"]


def test_low_stock_only_returns_items_at_or_below_threshold(client, admin_headers, category_id, warehouse_a_id):
    low_product = _make_product(client, admin_headers, category_id, "LOW-1", threshold=10)
    ok_product = _make_product(client, admin_headers, category_id, "OK-1", threshold=10)

    client.post(
        "/stock/in",
        json={"product_id": low_product, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": ok_product, "warehouse_id": warehouse_a_id, "quantity": 50},
        headers=admin_headers,
    )

    response = client.get("/stock/low-stock", headers=admin_headers)
    assert response.status_code == 200
    product_ids = {item["product"]["id"] for item in response.json()["items"]}
    assert low_product in product_ids
    assert ok_product not in product_ids


def test_low_stock_at_exact_threshold_is_included(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "EXACT-1", threshold=10)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )

    items = client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    assert any(item["product"]["id"] == product_id for item in items)


def test_movements_filter_by_product(client, admin_headers, category_id, warehouse_a_id):
    product_a = _make_product(client, admin_headers, category_id, "MOVE-A", threshold=0)
    product_b = _make_product(client, admin_headers, category_id, "MOVE-B", threshold=0)
    client.post(
        "/stock/in",
        json={"product_id": product_a, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_b, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )

    items = client.get(f"/stock/movements?product_id={product_a}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["product"]["id"] == product_a


def test_movements_filter_by_type(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product_id = _make_product(client, admin_headers, category_id, "TYPE-1", threshold=0)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 5,
        },
        headers=admin_headers,
    )

    items = client.get("/stock/movements?movement_type=out", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["movement_type"] == "out"


def test_movements_pagination(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "PAGE-1", threshold=0)
    for _ in range(5):
        client.post(
            "/stock/in",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
            headers=admin_headers,
        )

    page1 = client.get("/stock/movements?limit=2&offset=0", headers=admin_headers).json()
    page2 = client.get("/stock/movements?limit=2&offset=2", headers=admin_headers).json()
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert page1["total"] == 5
    assert {item["id"] for item in page1["items"]}.isdisjoint({item["id"] for item in page2["items"]})
