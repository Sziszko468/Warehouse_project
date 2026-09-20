from app.messages import Messages


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


def _confirmed_order(client, admin_headers, customer_id, warehouse_id, product_id, quantity=20, stock=None):
    _stock_in(client, admin_headers, product_id, warehouse_id, stock if stock is not None else quantity)
    payload = {
        "customer_id": customer_id,
        "warehouse_id": warehouse_id,
        "lines": [{"product_id": product_id, "quantity_ordered": quantity}],
    }
    order = client.post("/customer-orders", json=payload, headers=admin_headers).json()
    confirmed = client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    assert confirmed.status_code == 200
    return confirmed.json()


def _create_shipment(client, headers, order_id, line_id, quantity, carrier="Speedy Logistics"):
    return client.post(
        "/shipments",
        json={
            "customer_order_id": order_id,
            "carrier": carrier,
            "lines": [{"customer_order_line_id": line_id, "quantity": quantity}],
        },
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


def test_full_lifecycle_single_shipment(client, admin_headers, customer_id, warehouse_a_id, product_id):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20)
    line_id = order["lines"][0]["id"]

    created = _create_shipment(client, admin_headers, order["id"], line_id, 20)
    assert created.status_code == 201
    shipment = created.json()
    assert shipment["status"] == "pending"
    assert shipment["carrier"] == "Speedy Logistics"
    assert shipment["lines"][0]["quantity"] == 20

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 0
    assert row["reserved_quantity"] == 0

    updated_order = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert updated_order["status"] == "shipped"
    assert updated_order["shipped_at"] is not None
    assert updated_order["lines"][0]["quantity_shipped"] == 20

    dispatched = client.patch(f"/shipments/{shipment['id']}/dispatch", headers=admin_headers)
    assert dispatched.status_code == 200
    assert dispatched.json()["status"] == "in_transit"
    assert dispatched.json()["shipped_at"] is not None

    delivered = client.patch(f"/shipments/{shipment['id']}/deliver", headers=admin_headers)
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"
    assert delivered.json()["delivered_at"] is not None


def test_two_shipments_split_fulfillment(client, admin_headers, customer_id, warehouse_a_id, product_id):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20)
    line_id = order["lines"][0]["id"]

    first = _create_shipment(client, admin_headers, order["id"], line_id, 12)
    assert first.status_code == 201
    order_after_first = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert order_after_first["status"] == "partially_shipped"
    assert order_after_first["lines"][0]["quantity_shipped"] == 12

    second = _create_shipment(client, admin_headers, order["id"], line_id, 8)
    assert second.status_code == 201
    order_after_second = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert order_after_second["status"] == "shipped"
    assert order_after_second["lines"][0]["quantity_shipped"] == 20

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_over_shipment_rejected_and_nothing_applied(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=10)
    line_id = order["lines"][0]["id"]

    response = _create_shipment(client, admin_headers, order["id"], line_id, 11)
    assert response.status_code == 400

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 10
    assert row["reserved_quantity"] == 10
    unchanged_order = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert unchanged_order["status"] == "confirmed"
    assert unchanged_order["lines"][0]["quantity_shipped"] == 0


def test_shipment_against_draft_order_rejected(client, admin_headers, customer_id, warehouse_a_id, product_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    payload = {
        "customer_id": customer_id,
        "warehouse_id": warehouse_a_id,
        "lines": [{"product_id": product_id, "quantity_ordered": 5}],
    }
    order = client.post("/customer-orders", json=payload, headers=admin_headers).json()
    line_id = order["lines"][0]["id"]

    response = _create_shipment(client, admin_headers, order["id"], line_id, 5)
    assert response.status_code == 400


def test_shipment_line_not_on_order_404(client, admin_headers, customer_id, warehouse_a_id, product_id):
    order_a = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=10)
    order_b = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=10)
    wrong_line_id = order_a["lines"][0]["id"]

    response = _create_shipment(client, admin_headers, order_b["id"], wrong_line_id, 1)
    assert response.status_code == 404


def test_nonexistent_customer_order_404(client, admin_headers):
    response = client.post(
        "/shipments",
        json={"customer_order_id": 999999, "lines": [{"customer_order_line_id": 1, "quantity": 1}]},
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.CUSTOMER_ORDER_NOT_FOUND


# ---------------------------------------------------------------------------
# Cancel with reversal
# ---------------------------------------------------------------------------


def test_cancel_pending_shipment_reverses_stock_and_order(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=15)
    line_id = order["lines"][0]["id"]
    shipment = _create_shipment(client, admin_headers, order["id"], line_id, 15).json()

    response = client.post(f"/shipments/{shipment['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 15
    assert row["reserved_quantity"] == 15

    reverted_order = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert reverted_order["status"] == "confirmed"
    assert reverted_order["lines"][0]["quantity_shipped"] == 0


def test_cancel_one_of_two_shipments_reverts_to_partially_shipped(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=20)
    line_id = order["lines"][0]["id"]
    first = _create_shipment(client, admin_headers, order["id"], line_id, 12).json()
    _create_shipment(client, admin_headers, order["id"], line_id, 8)

    fully_shipped = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert fully_shipped["status"] == "shipped"

    response = client.post(f"/shipments/{first['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200

    after_cancel = client.get(f"/customer-orders/{order['id']}", headers=admin_headers).json()
    assert after_cancel["status"] == "partially_shipped"
    assert after_cancel["lines"][0]["quantity_shipped"] == 8

    row = _stock_row(client, admin_headers, product_id, warehouse_a_id)
    assert row["quantity"] == 12
    assert row["reserved_quantity"] == 12


def test_cancel_delivered_shipment_rejected(client, admin_headers, customer_id, warehouse_a_id, product_id):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    line_id = order["lines"][0]["id"]
    shipment = _create_shipment(client, admin_headers, order["id"], line_id, 5).json()
    client.patch(f"/shipments/{shipment['id']}/dispatch", headers=admin_headers)
    client.patch(f"/shipments/{shipment['id']}/deliver", headers=admin_headers)

    response = client.post(f"/shipments/{shipment['id']}/cancel", headers=admin_headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_staff_can_create_dispatch_and_deliver(
    client, staff_headers, admin_headers, customer_id, warehouse_a_id, product_id
):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    line_id = order["lines"][0]["id"]

    created = _create_shipment(client, staff_headers, order["id"], line_id, 5)
    assert created.status_code == 201
    shipment = created.json()
    assert client.patch(f"/shipments/{shipment['id']}/dispatch", headers=staff_headers).status_code == 200
    assert client.patch(f"/shipments/{shipment['id']}/deliver", headers=staff_headers).status_code == 200


def test_staff_cannot_cancel(client, staff_headers, admin_headers, customer_id, warehouse_a_id, product_id):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    line_id = order["lines"][0]["id"]
    shipment = _create_shipment(client, admin_headers, order["id"], line_id, 5).json()

    response = client.post(f"/shipments/{shipment['id']}/cancel", headers=staff_headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Customer order cancel is blocked once shipping has started (deferred from Phase 2)
# ---------------------------------------------------------------------------


def test_customer_order_cancel_rejected_once_shipping_started(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    order = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=10)
    line_id = order["lines"][0]["id"]
    _create_shipment(client, admin_headers, order["id"], line_id, 4)

    response = client.post(f"/customer-orders/{order['id']}/cancel", headers=admin_headers)
    assert response.status_code == 400
    assert response.json()["detail"] == Messages.CUSTOMER_ORDER_CANNOT_CANCEL


# ---------------------------------------------------------------------------
# List/get/404s
# ---------------------------------------------------------------------------


def test_get_nonexistent_404(client, admin_headers):
    response = client.get("/shipments/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.SHIPMENT_NOT_FOUND


def test_list_filters_by_customer_order(client, admin_headers, customer_id, warehouse_a_id, product_id):
    order_a = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    order_b = _confirmed_order(client, admin_headers, customer_id, warehouse_a_id, product_id, quantity=5)
    shipment_a = _create_shipment(client, admin_headers, order_a["id"], order_a["lines"][0]["id"], 5).json()
    _create_shipment(client, admin_headers, order_b["id"], order_b["lines"][0]["id"], 5)

    filtered = client.get(f"/shipments?customer_order_id={order_a['id']}", headers=admin_headers).json()["items"]
    ids = {s["id"] for s in filtered}
    assert ids == {shipment_a["id"]}


def test_unauthenticated_rejected(client):
    assert client.get("/shipments").status_code == 401
    assert client.post("/shipments", json={}).status_code == 401
