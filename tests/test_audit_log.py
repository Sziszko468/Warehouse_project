import pytest

from app.messages import Messages
from tests.resource_specs import ALL_SPECS, spec_id


def _logs_for(client, admin_headers, entity_type: str, entity_id: int) -> list[dict]:
    response = client.get(f"/audit-logs?entity_type={entity_type}&entity_id={entity_id}", headers=admin_headers)
    assert response.status_code == 200
    return response.json()["items"]


# ---------------------------------------------------------------------------
# Generic master-data hook (crud.common.create/update/soft_delete)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_create_produces_audit_row(client, admin_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    ).json()

    logs = _logs_for(client, admin_headers, spec.name.capitalize(), created["id"])
    assert len(logs) == 1
    assert logs[0]["action"] == "create"
    assert logs[0]["entity_id"] == created["id"]


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_update_produces_audit_row_with_changes(client, admin_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    ).json()
    client.patch(
        f"{spec.endpoint}/{created['id']}", json={spec.patch_field: spec.patch_value}, headers=admin_headers
    )

    logs = _logs_for(client, admin_headers, spec.name.capitalize(), created["id"])
    actions = [log["action"] for log in logs]
    assert actions == ["update", "create"]  # newest first
    assert spec.patch_field in logs[0]["changes"]


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_noop_update_produces_no_audit_row(client, admin_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    ).json()
    # PATCH with the field already set to its current value - nothing actually changes
    client.patch(
        f"{spec.endpoint}/{created['id']}",
        json={spec.patch_field: created[spec.patch_field]},
        headers=admin_headers,
    )

    logs = _logs_for(client, admin_headers, spec.name.capitalize(), created["id"])
    assert [log["action"] for log in logs] == ["create"]


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_soft_delete_produces_audit_row(client, admin_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    ).json()
    client.delete(f"{spec.endpoint}/{created['id']}", headers=admin_headers)

    logs = _logs_for(client, admin_headers, spec.name.capitalize(), created["id"])
    assert logs[0]["action"] == "soft_delete"


# ---------------------------------------------------------------------------
# Explicit service-layer status transitions
# ---------------------------------------------------------------------------


def test_purchase_order_lifecycle_produces_status_change_rows(
    client, admin_headers, supplier_id, warehouse_a_id, product_id
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
    line_id = po["lines"][0]["id"]
    client.post(
        f"/purchase-orders/{po['id']}/receive",
        json={"lines": [{"purchase_order_line_id": line_id, "quantity": 10}]},
        headers=admin_headers,
    )

    logs = _logs_for(client, admin_headers, "PurchaseOrder", po["id"])
    actions = [log["action"] for log in logs]
    assert actions == ["status_change", "status_change", "create"]  # newest first: receive, submit, create


def test_purchase_order_cancel_produces_status_change_row(
    client, admin_headers, supplier_id, warehouse_a_id, product_id
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
    client.post(f"/purchase-orders/{po['id']}/cancel", headers=admin_headers)

    logs = _logs_for(client, admin_headers, "PurchaseOrder", po["id"])
    assert logs[0]["action"] == "status_change"
    assert logs[0]["summary"] == "cancelled"


def test_customer_order_confirm_and_cancel_produce_status_change_rows(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    order = client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    client.post(f"/customer-orders/{order['id']}/cancel", headers=admin_headers)

    logs = _logs_for(client, admin_headers, "CustomerOrder", order["id"])
    actions = [log["action"] for log in logs]
    assert actions == ["status_change", "status_change", "create"]
    assert logs[0]["summary"] == "cancelled"
    assert logs[1]["summary"] == "confirmed"


def test_shipment_lifecycle_produces_status_change_rows(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    order = client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    line_id = order["lines"][0]["id"]
    shipment = client.post(
        "/shipments",
        json={"customer_order_id": order["id"], "lines": [{"customer_order_line_id": line_id, "quantity": 5}]},
        headers=admin_headers,
    ).json()
    client.patch(f"/shipments/{shipment['id']}/dispatch", headers=admin_headers)
    client.patch(f"/shipments/{shipment['id']}/deliver", headers=admin_headers)

    logs = _logs_for(client, admin_headers, "Shipment", shipment["id"])
    actions = [log["action"] for log in logs]
    assert actions == ["status_change", "status_change", "create"]  # newest first: deliver, dispatch, create


def test_shipment_cancel_produces_status_change_row(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    order = client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/customer-orders/{order['id']}/confirm", headers=admin_headers)
    line_id = order["lines"][0]["id"]
    shipment = client.post(
        "/shipments",
        json={"customer_order_id": order["id"], "lines": [{"customer_order_line_id": line_id, "quantity": 5}]},
        headers=admin_headers,
    ).json()
    client.post(f"/shipments/{shipment['id']}/cancel", headers=admin_headers)

    logs = _logs_for(client, admin_headers, "Shipment", shipment["id"])
    assert logs[0]["action"] == "status_change"
    assert logs[0]["summary"] == "cancelled"


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def test_staff_cannot_list_audit_logs(client, staff_headers):
    assert client.get("/audit-logs", headers=staff_headers).status_code == 403


def test_admin_can_list_audit_logs(client, admin_headers, category_id):
    response = client.get("/audit-logs", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] > 0


def test_unauthenticated_rejected(client):
    assert client.get("/audit-logs").status_code == 401


def test_get_nonexistent_404(client, admin_headers):
    response = client.get("/audit-logs/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == Messages.AUDIT_LOG_NOT_FOUND


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_by_action(client, admin_headers, category_id):
    updated = client.patch(
        f"/categories/{category_id}", json={"description": "Updated"}, headers=admin_headers
    ).json()

    create_only = client.get(
        f"/audit-logs?entity_type=Category&entity_id={updated['id']}&action=create", headers=admin_headers
    ).json()["items"]
    assert len(create_only) == 1
    assert create_only[0]["action"] == "create"

    update_only = client.get(
        f"/audit-logs?entity_type=Category&entity_id={updated['id']}&action=update", headers=admin_headers
    ).json()["items"]
    assert len(update_only) == 1
    assert update_only[0]["action"] == "update"


def test_filter_by_performed_by(client, admin_headers, admin_user, category_id):
    logs = client.get(f"/audit-logs?performed_by_id={admin_user.id}", headers=admin_headers).json()["items"]
    assert len(logs) > 0
    assert all(log["performed_by"]["id"] == admin_user.id for log in logs)
