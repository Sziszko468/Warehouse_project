import pytest


@pytest.fixture
def category_id(client, admin_headers) -> int:
    return client.post("/categories", json={"name": "Cables"}, headers=admin_headers).json()["id"]


@pytest.fixture
def product_id(client, admin_headers, category_id) -> int:
    payload = {
        "sku": "SKU-1",
        "name": "USB Cable",
        "category_id": category_id,
        "unit_price": "4.99",
        "min_stock_threshold": 5,
    }
    return client.post("/products", json=payload, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_a_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse A"}, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_b_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse B"}, headers=admin_headers).json()["id"]


def _quantity_at(client, headers, product_id, warehouse_id) -> int:
    resp = client.get(f"/stock?product_id={product_id}&warehouse_id={warehouse_id}", headers=headers)
    items = resp.json()["items"]
    return items[0]["quantity"] if items else 0


def test_stock_in_creates_stock_and_movement(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 50},
        headers=admin_headers,
    )
    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "in"
    assert movement["quantity"] == 50
    assert movement["to_warehouse"]["id"] == warehouse_a_id
    assert movement["from_warehouse"] is None
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 50


def test_stock_in_increments_existing(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 30},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 50


def test_stock_out_sufficient(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 50},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 30


def test_stock_out_insufficient_leaves_quantity_unchanged(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 999},
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 10


def test_stock_out_never_stocked_pair_is_409_not_404(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_transfer_sufficient(client, admin_headers, product_id, warehouse_a_id, warehouse_b_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 50},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 20,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "transfer"
    assert movement["from_warehouse"]["id"] == warehouse_a_id
    assert movement["to_warehouse"]["id"] == warehouse_b_id
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 30
    assert _quantity_at(client, admin_headers, product_id, warehouse_b_id) == 20


def test_transfer_insufficient_leaves_source_unchanged(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 999,
        },
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 10


def test_transfer_same_warehouse_rejected(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_a_id,
            "quantity": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 400


@pytest.mark.parametrize("endpoint", ["/stock/in", "/stock/out"])
def test_zero_quantity_rejected(client, admin_headers, product_id, warehouse_a_id, endpoint):
    response = client.post(
        endpoint,
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 0},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_unauthenticated_rejected_on_all_stock_ops(client, product_id, warehouse_a_id):
    assert (
        client.post(
            "/stock/in", json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/stock/out", json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/stock/transfer",
            json={
                "product_id": product_id,
                "from_warehouse_id": warehouse_a_id,
                "to_warehouse_id": warehouse_a_id,
                "quantity": 1,
            },
        ).status_code
        == 401
    )


def test_staff_can_perform_all_stock_operations(client, staff_headers, product_id, warehouse_a_id, warehouse_b_id):
    assert (
        client.post(
            "/stock/in",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 50},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/out",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/transfer",
            json={
                "product_id": product_id,
                "from_warehouse_id": warehouse_a_id,
                "to_warehouse_id": warehouse_b_id,
                "quantity": 10,
            },
            headers=staff_headers,
        ).status_code
        == 201
    )
