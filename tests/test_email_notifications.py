import pytest

from app.services import email_service
from tests.constants import LOW_STOCK_THRESHOLD


class RecordingEmailSender:
    def __init__(self):
        self.sent = []

    def send(self, *, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})


@pytest.fixture
def recorder(monkeypatch):
    rec = RecordingEmailSender()
    monkeypatch.setattr(email_service, "get_email_sender", lambda: rec)
    # Sidesteps a cross-session visibility subtlety of the SQLite-in-memory test harness (the
    # background task opens its own SessionLocal(), a different Session object than the request's
    # `db_session` fixture) - what's under test here is *when* a notification fires and with what
    # content, not the admin-recipient lookup query itself.
    monkeypatch.setattr(email_service, "_active_admin_emails", lambda: ["admin@stockflow.com"])
    return rec


def _stock_in(client, admin_headers, product_id, warehouse_id, quantity):
    return client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_id, "quantity": quantity},
        headers=admin_headers,
    )


# ---------------------------------------------------------------------------
# Purchase orders
# ---------------------------------------------------------------------------


def test_purchase_order_submit_sends_email(
    client, admin_headers, recorder, supplier_id, warehouse_a_id, product_id
):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10, "unit_price": "5.00"}],
        },
        headers=admin_headers,
    ).json()

    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)

    assert len(recorder.sent) == 1
    assert recorder.sent[0]["to"] == ["admin@stockflow.com"]
    assert f"PO-{po['id']}" in recorder.sent[0]["subject"]
    assert "submitted" in recorder.sent[0]["subject"]


def test_purchase_order_full_receive_sends_email(
    client, admin_headers, recorder, supplier_id, warehouse_a_id, product_id
):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10, "unit_price": "5.00"}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    recorder.sent.clear()
    line_id = po["lines"][0]["id"]

    client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 10}]},
        headers=admin_headers,
    )

    assert len(recorder.sent) == 1
    assert "received" in recorder.sent[0]["subject"]


def test_purchase_order_partial_receive_does_not_send_received_email(
    client, admin_headers, recorder, supplier_id, warehouse_a_id, product_id
):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10, "unit_price": "5.00"}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)
    recorder.sent.clear()
    line_id = po["lines"][0]["id"]

    client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 4}]},
        headers=admin_headers,
    )

    assert recorder.sent == []


# ---------------------------------------------------------------------------
# Customer orders / shipments
# ---------------------------------------------------------------------------


def test_shipment_full_fulfillment_sends_email(
    client, admin_headers, recorder, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    order = client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    recorder.sent.clear()
    line_id = order["lines"][0]["id"]

    client.post(
        "/shipments",
        json={"customer_order_id": order["id"], "lines": [{"customer_order_line_id": line_id, "quantity": 10}]},
        headers=admin_headers,
    )

    assert len(recorder.sent) == 1
    assert f"CO-{order['id']}" in recorder.sent[0]["subject"]
    assert "shipped" in recorder.sent[0]["subject"]


def test_shipment_partial_fulfillment_does_not_send_email(
    client, admin_headers, recorder, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
    order = client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    recorder.sent.clear()
    line_id = order["lines"][0]["id"]

    client.post(
        "/shipments",
        json={"customer_order_id": order["id"], "lines": [{"customer_order_line_id": line_id, "quantity": 4}]},
        headers=admin_headers,
    )

    assert recorder.sent == []


# ---------------------------------------------------------------------------
# Low stock
# ---------------------------------------------------------------------------


def test_low_stock_crossing_sends_once(client, admin_headers, recorder, category_id, warehouse_a_id):
    product = client.post(
        "/products",
        json={
            "sku": "EMAIL-LOW-1",
            "name": "Low Stock Widget",
            "category_id": category_id,
            "unit_price": "1.00",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()
    _stock_in(client, admin_headers, product["id"], warehouse_a_id, LOW_STOCK_THRESHOLD + 10)
    recorder.sent.clear()

    # crosses from above the threshold to at-or-below it
    response = client.post(
        "/stock/out",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert len(recorder.sent) == 1
    assert "Low stock" in recorder.sent[0]["subject"]

    # already at/below threshold - a further stock/out must not re-send
    recorder.sent.clear()
    client.post(
        "/stock/out",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert recorder.sent == []


def test_low_stock_not_triggered_when_staying_above_threshold(
    client, admin_headers, recorder, category_id, warehouse_a_id
):
    product = client.post(
        "/products",
        json={
            "sku": "EMAIL-LOW-2",
            "name": "Healthy Stock Widget",
            "category_id": category_id,
            "unit_price": "1.00",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()
    _stock_in(client, admin_headers, product["id"], warehouse_a_id, 100)
    recorder.sent.clear()

    client.post(
        "/stock/out",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    assert recorder.sent == []


# ---------------------------------------------------------------------------
# LogEmailSender
# ---------------------------------------------------------------------------


def test_log_email_sender_never_raises():
    email_service.LogEmailSender().send(to=["a@example.com"], subject="Test", body="Body")
