from app.messages import Messages
from tests.constants import SAMPLE_UNIT_PRICE


def _stock_row(client, headers, product_id, warehouse_id) -> dict | None:
    items = client.get(f"/stock?product_id={product_id}&warehouse_id={warehouse_id}", headers=headers).json()[
        "items"
    ]
    return items[0] if items else None


def _stock_in(client, admin_headers, product_id, warehouse_id, quantity):
    return client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_id, "quantity": quantity},
        headers=admin_headers,
    )


def _create_co(client, headers, customer_id, warehouse_id, product_id, quantity=10):
    payload = {
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "lines": [{"product_id": product_id, "quantity_ordered": quantity}],
    }
    return client.post("/customer-orders", json=payload, headers=headers)


# ---------------------------------------------------------------------------
# Create validation
# ---------------------------------------------------------------------------


def test_create_requires_at_least_one_line(client, admin_headers, customer_id, warehouse_a_id):
    response = client.post(
        "/customer-orders",
        json={"customer_id": customer_id, "warehouse_id": warehouse_a_id, "lines": []},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_create_rejects_inactive_customer(client, admin_headers, customer_id, warehouse_a_id, product_id):
    assert client.delete(f"/customers/{customer_id}", headers=admin_headers).status_code == 204
    response = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CUSTOMER_NOT_FOUND


def test_create_rejects_inactive_warehouse(client, admin_headers, customer_id, warehouse_a_id, product_id):
    assert client.delete(f"/warehouses/{warehouse_a_id}", headers=admin_headers).status_code == 204
    response = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.WAREHOUSE_NOT_FOUND


def test_create_rejects_inactive_product(client, admin_headers, customer_id, warehouse_a_id, product_id):
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    response = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.PRODUCT_NOT_FOUND


def test_create_snapshots_unit_price_from_product(client, admin_headers, customer_id, warehouse_a_id, product_id):
    response = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=3)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["lines"][0]["unit_price"] == SAMPLE_UNIT_PRICE
    assert body["lines"][0]["quantity_shipped"] == 0


# ---------------------------------------------------------------------------
# Confirm reserves stock
# ---------------------------------------------------------------------------


def test_confirm_reserves_stock(client, admin_headers, customer_id, warehouse_a_id, product_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 50)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20).json()

    response = client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"
    assert response.json()["confirmed_at"] is not None

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 50
    assert row["reserved_quantity"] == 20
    assert row["available_quantity"] == 30


def test_confirm_fails_with_insufficient_available_stock(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 5)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20).json()

    response = client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    assert response.status_code == 409

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["reserved_quantity"] == 0


def test_confirm_all_or_nothing_across_lines(client, admin_headers, customer_id, warehouse_a_id, category_id):
    product_a = client.post(
        "/products",
        json={"sku": "CO-A", "name": "A", "category_id": category_id, "unit_price": "1.00"},
        headers=admin_headers,
    ).json()
    product_b = client.post(
        "/products",
        json={"sku": "CO-B", "name": "B", "category_id": category_id, "unit_price": "1.00"},
        headers=admin_headers,
    ).json()
    _stock_in(client, admin_headers, product_a["id"], warehouse_a_id, 100)
    _stock_in(client, admin_headers, product_b["id"], warehouse_a_id, 2)  # not enough for the order below

    payload = {
        "customer_id": customer_id,
        "warehouse_id": warehouse_a_id,
        "lines": [
            {"product_id": product_a["id"], "quantity_ordered": 10},
            {"product_id": product_b["id"], "quantity_ordered": 10},
        ],
    }
    order = client.post("/customer-orders", json=payload, headers=admin_headers).json()
    response = client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    assert response.status_code == 409

    # product A must not have been left partially reserved even though it alone had enough stock
    row_a = _stock_row(client, admin_headers, product_a["id"], warehouse_a_id)
    assert row_a["reserved_quantity"] == 0


def test_manual_stock_out_rejected_when_it_would_cut_into_reserved_stock(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 20)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)

    # all 20 units are now reserved for the confirmed order - nothing should be manually shippable
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_manual_transfer_rejected_when_it_would_cut_into_reserved_stock(
    client, admin_headers, customer_id, warehouse_a_id, warehouse_b_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 20)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)

    response = client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


def test_cancel_from_draft_does_not_touch_stock(client, admin_headers, customer_id, warehouse_a_id, product_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5).json()

    response = client.post(f"/customer-orders/{order['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["reserved_quantity"] == 0


def test_cancel_from_confirmed_releases_reservation(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=7).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)

    row_confirmed = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row_confirmed["reserved_quantity"] == 7

    response = client.post(f"/customer-orders/{order['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    row_after = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row_after["reserved_quantity"] == 0
    assert row_after["quantity"] == 10


def test_confirm_before_confirm_rejected_twice(client, admin_headers, customer_id, warehouse_a_id, product_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    response = client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Roles - staff-allowed per the confirmed permission split
# ---------------------------------------------------------------------------


def test_staff_can_create_confirm_and_cancel(
    client, staff_headers, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    create_response = _create_co(client, staff_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    assert create_response.status_code == 201
    order = create_response.json()

    assert client.post(f"/customer-orders/{order['id']}/confirm", headers=staff_headers).status_code == 200
    assert client.post(f"/customer-orders/{order['id']}/cancel", headers=staff_headers).status_code == 200


# ---------------------------------------------------------------------------
# List/get/404s
# ---------------------------------------------------------------------------


def test_list_filters_by_status(client, admin_headers, customer_id, warehouse_a_id, product_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    draft_order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id).json()
    confirmed_order = _create_co(client, admin_headers, customer_id, warehouse_a_id, product_id).json()
    client.post(f"/customer-orders/{confirmed_order['id']}/confirm", headers=admin_headers)

    confirmed_only = client.get("/customer-orders?status=confirmed", headers=admin_headers).json()["items"]
    ids = {order["id"] for order in confirmed_only}
    assert confirmed_order["id"] in ids
    assert draft_order["id"] not in ids


def test_get_nonexistent_404(client, admin_headers):
    response = client.get("/customer-orders/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CUSTOMER_ORDER_NOT_FOUND


def test_unauthenticated_rejected(client, customer_id, warehouse_a_id, product_id):
    payload = {
        "customer_id": customer_id,
        "warehouse_id": warehouse_a_id,
        "lines": [{"product_id": product_id, "quantity_ordered": 1}],
    }
    assert client.post("/customer-orders", json=payload).status_code == 401
    assert client.get("/customer-orders").status_code == 401
