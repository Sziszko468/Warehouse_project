import pytest

from tests.constants import EXCESS_QUANTITY, LARGE_QUANTITY, SMALL_QUANTITY

# category_id, product_id, warehouse_a_id, warehouse_b_id are shared fixtures from conftest.py

STOCK_ENDPOINTS = ["/stock/in", "/stock/out"]


def _quantity_at(client, headers, product_id, warehouse_id) -> int:
    resp = client.get(f"/stock?product_id={product_id}&warehouse_id={warehouse_id}", headers=headers)
    items = resp.json()["items"]
    return items[0]["quantity"] if items else 0


def _transfer_payload(product_id, from_id, to_id, quantity) -> dict:
    return {"product_id": product_id, "from_warehouse_id": from_id, "to_warehouse_id": to_id, "quantity": quantity}


# ---------------------------------------------------------------------------
# Basic operation correctness
# ---------------------------------------------------------------------------


def test_stock_in_creates_stock_and_movement(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": LARGE_QUANTITY},
        headers=admin_headers,
    )
    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "in"
    assert movement["quantity"] == LARGE_QUANTITY
    assert movement["to_warehouse"]["id"] == warehouse_a_id
    assert movement["from_warehouse"] is None
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == LARGE_QUANTITY


def test_stock_in_increments_existing(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == SMALL_QUANTITY * 2


def test_stock_in_note_is_persisted(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/in",
        json={
            "product_id": product_id,
            "warehouse_id": warehouse_a_id,
            "quantity": SMALL_QUANTITY,
            "note": "PO-42",
        },
        headers=admin_headers,
    )
    assert response.json()["note"] == "PO-42"


def test_stock_in_records_performing_user(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    me = client.get("/auth/me", headers=admin_headers).json()
    assert response.json()["performed_by"]["id"] == me["id"]


def test_stock_out_sufficient(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": LARGE_QUANTITY},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == LARGE_QUANTITY - SMALL_QUANTITY


def test_stock_out_insufficient_leaves_quantity_unchanged(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": EXCESS_QUANTITY},
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == SMALL_QUANTITY


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
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": LARGE_QUANTITY},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, SMALL_QUANTITY),
        headers=admin_headers,
    )
    assert response.status_code == 201
    movement = response.json()
    assert movement["movement_type"] == "transfer"
    assert movement["from_warehouse"]["id"] == warehouse_a_id
    assert movement["to_warehouse"]["id"] == warehouse_b_id
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == LARGE_QUANTITY - SMALL_QUANTITY
    assert _quantity_at(client, admin_headers, product_id, warehouse_b_id) == SMALL_QUANTITY


def test_transfer_insufficient_leaves_source_unchanged(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id
):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, EXCESS_QUANTITY),
        headers=admin_headers,
    )
    assert response.status_code == 409
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == SMALL_QUANTITY


def test_transfer_same_warehouse_rejected(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_a_id, 1),
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_multi_step_sequential_quantity_tracking(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id
):
    """A short in -> out -> transfer -> out chain, asserting the running total after every step -
    catches any state that only "looks" correct after a single operation."""
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 100},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 100

    client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 30},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 70

    client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, 25),
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_a_id) == 45
    assert _quantity_at(client, admin_headers, product_id, warehouse_b_id) == 25

    client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_b_id, "quantity": 25},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product_id, warehouse_b_id) == 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", STOCK_ENDPOINTS)
@pytest.mark.parametrize("bad_quantity", [0, -1, -100])
def test_non_positive_quantity_rejected(client, admin_headers, product_id, warehouse_a_id, endpoint, bad_quantity):
    response = client.post(
        endpoint,
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": bad_quantity},
        headers=admin_headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("bad_quantity", [0, -1, -100])
def test_transfer_non_positive_quantity_rejected(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id, bad_quantity
):
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, bad_quantity),
        headers=admin_headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", STOCK_ENDPOINTS)
def test_non_integer_quantity_rejected(client, admin_headers, product_id, warehouse_a_id, endpoint):
    response = client.post(
        endpoint,
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": "not-a-number"},
        headers=admin_headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", STOCK_ENDPOINTS)
def test_missing_product_id_rejected(client, admin_headers, warehouse_a_id, endpoint):
    response = client.post(endpoint, json={"warehouse_id": warehouse_a_id, "quantity": 1}, headers=admin_headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 404s for nonexistent references
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", STOCK_ENDPOINTS)
def test_nonexistent_product_404(client, admin_headers, warehouse_a_id, endpoint):
    response = client.post(
        endpoint, json={"product_id": 999999, "warehouse_id": warehouse_a_id, "quantity": 1}, headers=admin_headers
    )
    assert response.status_code == 404


@pytest.mark.parametrize("endpoint", STOCK_ENDPOINTS)
def test_nonexistent_warehouse_404(client, admin_headers, product_id, endpoint):
    response = client.post(
        endpoint, json={"product_id": product_id, "warehouse_id": 999999, "quantity": 1}, headers=admin_headers
    )
    assert response.status_code == 404


def test_transfer_nonexistent_product_404(client, admin_headers, warehouse_a_id, warehouse_b_id):
    response = client.post(
        "/stock/transfer", json=_transfer_payload(999999, warehouse_a_id, warehouse_b_id, 1), headers=admin_headers
    )
    assert response.status_code == 404


def test_transfer_nonexistent_from_warehouse_404(client, admin_headers, product_id, warehouse_b_id):
    response = client.post(
        "/stock/transfer", json=_transfer_payload(product_id, 999999, warehouse_b_id, 1), headers=admin_headers
    )
    assert response.status_code == 404


def test_transfer_nonexistent_to_warehouse_404(client, admin_headers, product_id, warehouse_a_id):
    response = client.post(
        "/stock/transfer", json=_transfer_payload(product_id, warehouse_a_id, 999999, 1), headers=admin_headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Soft-deleted product/warehouse rejected on every operation, not just stock/in
# ---------------------------------------------------------------------------


def test_stock_in_rejects_soft_deleted_warehouse(client, admin_headers, product_id, warehouse_a_id):
    assert client.delete(f"/warehouses/{warehouse_a_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_stock_in_rejects_soft_deleted_product(client, admin_headers, product_id, warehouse_a_id):
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_stock_out_rejects_soft_deleted_warehouse(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    assert client.delete(f"/warehouses/{warehouse_a_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_stock_out_rejects_soft_deleted_product(client, admin_headers, product_id, warehouse_a_id):
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
        headers=admin_headers,
    )
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_transfer_rejects_soft_deleted_product(client, admin_headers, product_id, warehouse_a_id, warehouse_b_id):
    assert client.delete(f"/products/{product_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, 1),
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_transfer_rejects_soft_deleted_from_warehouse(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id
):
    assert client.delete(f"/warehouses/{warehouse_a_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, 1),
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_transfer_rejects_soft_deleted_to_warehouse(
    client, admin_headers, product_id, warehouse_a_id, warehouse_b_id
):
    assert client.delete(f"/warehouses/{warehouse_b_id}", headers=admin_headers).status_code == 204
    response = client.post(
        "/stock/transfer",
        json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, 1),
        headers=admin_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


def test_unauthenticated_rejected_on_all_stock_ops(client, product_id, warehouse_a_id, warehouse_b_id):
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
            "/stock/transfer", json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, 1)
        ).status_code
        == 401
    )


def test_staff_can_perform_all_stock_operations(client, staff_headers, product_id, warehouse_a_id, warehouse_b_id):
    assert (
        client.post(
            "/stock/in",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": LARGE_QUANTITY},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/out",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": SMALL_QUANTITY},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/transfer",
            json=_transfer_payload(product_id, warehouse_a_id, warehouse_b_id, SMALL_QUANTITY),
            headers=staff_headers,
        ).status_code
        == 201
    )
