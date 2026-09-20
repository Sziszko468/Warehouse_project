from app.messages import Messages
from tests.constants import SAMPLE_UNIT_PRICE


def _quantity_at(client, headers, product_id, warehouse_id) -> int:
    items = client.get(f"/stock?product_id={product_id}&warehouse_id={warehouse_id}", headers=headers).json()[
        "items"
    ]
    return items[0]["quantity"] if items else 0


def _create_po(client, admin_headers, supplier_id, warehouse_id, product_id, quantity=10, unit_price="5.00"):
    payload = {
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_id,
        "lines": [{"product_id": product_id, "quantity_ordered": quantity, "unit_price": unit_price}],
    }
    return client.post("/purchase-orders", json=payload, headers=admin_headers)


# ---------------------------------------------------------------------------
# Create validation
# ---------------------------------------------------------------------------


def test_create_requires_at_least_one_line(client, admin_headers, supplier_id, warehouse_a_id):
    response = client.post(
        "/purchase-orders",
        json={"supplier_id": supplier_id, "warehouse_id": warehouse_a_id, "lines": []},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_create_rejects_inactive_supplier(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    assert client.delete(f"/suppliers/{supplier_id}", headers=admin_headers).status_code == 204
    response = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.SUPPLIER_NOT_FOUND


def test_create_rejects_inactive_warehouse(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    assert client.delete(f"/warehouses/{warehouse_a_id}", headers=admin_headers).status_code == 204
    response = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.WAREHOUSE_NOT_FOUND


def test_create_rejects_inactive_product(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    response = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.PRODUCT_NOT_FOUND


def test_create_returns_draft_status(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    response = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=10)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["lines"][0]["quantity_ordered"] == 10
    assert body["lines"][0]["quantity_received"] == 0
    assert body["supplier"]["id"] == supplier_id
    assert body["warehouse"]["id"] == warehouse_a_id


# ---------------------------------------------------------------------------
# Lifecycle: draft -> submit -> receive (full and partial) -> cancel
# ---------------------------------------------------------------------------


def test_full_lifecycle_receive_in_full(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=20).json()

    submitted = client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["submitted_at"] is not None

    line_id = po["lines"][0]["id"]
    received = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 20}]},
        headers=admin_headers,
    )
    assert received.status_code == 200
    body = received.json()
    assert body["status"] == "received"
    assert body["received_at"] is not None
    assert body["lines"][0]["quantity_received"] == 20

    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 20
    movements = client.get(f"/stock/movements?product_id={product_id}", headers=admin_headers).json()["items"]
    assert len(movements) == 1
    assert movements[0]["movement_type"] == "in"
    assert f"PO #{po['id']}" in movements[0]["note"]


def test_partial_receive_across_two_calls(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=20).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    line_id = po["lines"][0]["id"]

    first = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 12}]},
        headers=admin_headers,
    )
    assert first.status_code == 200
    assert first.json()["status"] == "partially_received"
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 12

    second = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 8}]},
        headers=admin_headers,
    )
    assert second.status_code == 200
    assert second.json()["status"] == "received"
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 20


def test_over_receipt_rejected(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=10).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    line_id = po["lines"][0]["id"]

    response = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 11}]},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 0


def test_receive_before_submit_rejected(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=10).json()
    line_id = po["lines"][0]["id"]
    response = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 1}]},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_cancel_from_draft(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    response = client.post(f"/purchase-orders/{po['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancelled_at"] is not None


def test_cancel_from_submitted(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    response = client.post(f"/purchase-orders/{po['id']}/cancel", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_rejected_once_partially_received(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=10).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    line_id = po["lines"][0]["id"]
    client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 1}]},
        headers=admin_headers,
    )
    response = client.post(f"/purchase-orders/{po['id']}/cancel", headers=admin_headers)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def test_staff_cannot_create_submit_or_cancel(
    client, staff_headers, admin_headers, supplier_id, warehouse_a_id, product_id
):
    create_response = _create_po(client, staff_headers, supplier_id, warehouse_a_id, product_id)
    assert create_response.status_code == 403

    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    assert client.post(f"/purchase-orders/{po['id']}/submit", headers=staff_headers).status_code == 403
    assert client.post(f"/purchase-orders/{po['id']}/cancel", headers=staff_headers).status_code == 403


def test_staff_can_receive(client, staff_headers, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id, quantity=5).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    line_id = po["lines"][0]["id"]
    response = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 5}]},
        headers=staff_headers,
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# List/get/404s
# ---------------------------------------------------------------------------


def test_list_filters_by_status(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    draft_po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    submitted_po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    client.post(f"/purchase-orders/{submitted_po['id']}/submit", headers=admin_headers)

    submitted_only = client.get("/purchase-orders?status=submitted", headers=admin_headers).json()["items"]
    ids = {po["id"] for po in submitted_only}
    assert submitted_po["id"] in ids
    assert draft_po["id"] not in ids


def test_get_nonexistent_404(client, admin_headers):
    response = client.get("/purchase-orders/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.PURCHASE_ORDER_NOT_FOUND


def test_receive_nonexistent_line_404(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = _create_po(client, admin_headers, supplier_id, warehouse_a_id, product_id).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    response = client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": 999999, "quantity": 1}]},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_unauthenticated_rejected(client, supplier_id, warehouse_a_id, product_id):
    payload = {
        "supplier_id": supplier_id,
        "warehouse_id": warehouse_a_id,
        "lines": [{"product_id": product_id, "quantity_ordered": 1, "unit_price": SAMPLE_UNIT_PRICE}],
    }
    assert client.post("/purchase-orders", json=payload).status_code == 401
    assert client.get("/purchase-orders").status_code == 401
