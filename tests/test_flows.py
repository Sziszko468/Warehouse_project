"""End-to-end scenario tests. Unlike the rest of the suite, these are deliberately few, thorough,
and not parametrized - each walks through a realistic multi-step sequence of calls the way an
actual user session would, checking state after every step rather than just the final result.
"""

from app.messages import Messages
from tests.constants import LOW_STOCK_THRESHOLD, SAMPLE_PASSWORD


def _quantity_at(client, headers, product_id, warehouse_id) -> int:
    items = client.get(f"/stock?product_id={product_id}&warehouse_id={warehouse_id}", headers=headers).json()[
        "items"
    ]
    return items[0]["quantity"] if items else 0


def test_electronics_wholesaler_onboarding_flow(client, admin_headers):
    """A fresh shop is set up from nothing: categories, a supplier, warehouses, products, initial
    stock - then the low-stock view and the movement log are both checked against what actually
    happened, the way an admin would sanity-check the system after data entry."""
    category = client.post("/categories", json={"name": "Networking"}, headers=admin_headers).json()
    supplier = client.post(
        "/suppliers", json={"name": "NordicParts AB", "email": "sales@nordicparts.example"}, headers=admin_headers
    ).json()
    warehouse = client.post(
        "/warehouses",
        json={"name": "Budapest Central", "address": "Konyves Kalman krt. 12"},
        headers=admin_headers,
    ).json()

    router = client.post(
        "/products",
        json={
            "sku": "NET-RT-AX",
            "name": "Wi-Fi 6 Router",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
            "unit_price": "89.90",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()
    switch = client.post(
        "/products",
        json={
            "sku": "NET-SW-24P",
            "name": "24-Port Gigabit Switch",
            "category_id": category["id"],
            "supplier_id": supplier["id"],
            "unit_price": "129.00",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()

    client.post(
        "/stock/in",
        json={
            "product_id": router["id"],
            "warehouse_id": warehouse["id"],
            "quantity": 40,
            "note": "Initial shipment",
        },
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        # deliberately below the threshold, to prove the low-stock view picks it up immediately
        json={
            "product_id": switch["id"],
            "warehouse_id": warehouse["id"],
            "quantity": 3,
            "note": "Initial shipment",
        },
        headers=admin_headers,
    )

    assert _quantity_at(client, admin_headers, router["id"], warehouse["id"]) == 40
    assert _quantity_at(client, admin_headers, switch["id"], warehouse["id"]) == 3

    low_stock_ids = {
        item["product"]["id"] for item in client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    }
    assert switch["id"] in low_stock_ids
    assert router["id"] not in low_stock_ids

    movements = client.get("/stock/movements", headers=admin_headers).json()["items"]
    assert len(movements) == 2
    assert {m["product"]["id"] for m in movements} == {router["id"], switch["id"]}
    assert all(m["movement_type"] == "in" for m in movements)
    assert all(m["note"] == "Initial shipment" for m in movements)


def test_order_fulfillment_flow(client, admin_headers, category_id, warehouse_a_id):
    """A shipment arrives, then several customer orders are fulfilled from it via stock/out. One
    order is too large for what's left and must fail cleanly, without disturbing stock already
    committed to the orders fulfilled before it."""
    product = client.post(
        "/products",
        json={"sku": "PRF-MS-WL", "name": "Wireless Mouse", "category_id": category_id, "unit_price": "24.90"},
        headers=admin_headers,
    ).json()

    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 50, "note": "PO-1001"},
        headers=admin_headers,
    )
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == 50

    order_quantities = [12, 8, 15]  # orders 1-3: fulfillable, leaves 15 in stock
    for order_number, quantity in enumerate(order_quantities, start=1):
        response = client.post(
            "/stock/out",
            json={
                "product_id": product["id"],
                "warehouse_id": warehouse_a_id,
                "quantity": quantity,
                "note": f"Order-{order_number}",
            },
            headers=admin_headers,
        )
        assert response.status_code == 201

    remaining_after_first_three = 50 - sum(order_quantities)
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == remaining_after_first_three

    # order 4 asks for more than the 15 units left - must fail without touching stock
    failing_response = client.post(
        "/stock/out",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 20, "note": "Order-4"},
        headers=admin_headers,
    )
    assert failing_response.status_code == 409
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == remaining_after_first_three

    # a right-sized order 4 succeeds afterwards, proving the failed attempt didn't corrupt state
    final_response = client.post(
        "/stock/out",
        json={
            "product_id": product["id"],
            "warehouse_id": warehouse_a_id,
            "quantity": remaining_after_first_three,
            "note": "Order-4-retry",
        },
        headers=admin_headers,
    )
    assert final_response.status_code == 201
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == 0

    movements = client.get(f"/stock/movements?product_id={product['id']}", headers=admin_headers).json()["items"]
    # 1 stock-in + 3 fulfilled orders + 1 successful retry = 5 movements; the failed order-4
    # attempt must not have left a ledger row at all
    assert len(movements) == 5
    notes = {m["note"] for m in movements}
    assert "Order-4" not in notes
    assert "Order-4-retry" in notes


def test_multi_warehouse_transfer_chain_flow(client, admin_headers, category_id):
    """One batch of stock moves through three warehouses via sequential transfers; quantities and
    the from/to trail in the movement log are both checked at every hop."""
    product = client.post(
        "/products",
        json={
            "sku": "MON-27-4K",
            "name": "27-inch 4K Monitor",
            "category_id": category_id,
            "unit_price": "349.00",
        },
        headers=admin_headers,
    ).json()
    warehouses = [
        client.post("/warehouses", json={"name": f"Hop {i}"}, headers=admin_headers).json() for i in range(3)
    ]
    hop_ids = [w["id"] for w in warehouses]

    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": hop_ids[0], "quantity": 30},
        headers=admin_headers,
    )

    # hop_ids and hop_ids[1:] are deliberately different lengths (a sliding pairwise window over
    # the chain), so strict=False here - not omitted, to make that intentional to a reader/linter.
    for source, destination in zip(hop_ids, hop_ids[1:], strict=False):
        response = client.post(
            "/stock/transfer",
            json={
                "product_id": product["id"],
                "from_warehouse_id": source,
                "to_warehouse_id": destination,
                "quantity": 30,
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        assert _quantity_at(client, admin_headers, product["id"], source) == 0
        assert _quantity_at(client, admin_headers, product["id"], destination) == 30

    # the stock ends up entirely at the last hop, with nothing left at the first two
    assert _quantity_at(client, admin_headers, product["id"], hop_ids[0]) == 0
    assert _quantity_at(client, admin_headers, product["id"], hop_ids[1]) == 0
    assert _quantity_at(client, admin_headers, product["id"], hop_ids[2]) == 30

    transfers = client.get(
        f"/stock/movements?product_id={product['id']}&movement_type=transfer", headers=admin_headers
    ).json()["items"]
    assert len(transfers) == 2
    # newest first: the second hop (1 -> 2) should be reported before the first hop (0 -> 1)
    assert transfers[0]["from_warehouse"]["id"] == hop_ids[1]
    assert transfers[0]["to_warehouse"]["id"] == hop_ids[2]
    assert transfers[1]["from_warehouse"]["id"] == hop_ids[0]
    assert transfers[1]["to_warehouse"]["id"] == hop_ids[1]


def test_staff_day_to_day_flow(client, admin_headers, staff_headers, category_id, warehouse_a_id, warehouse_b_id):
    """One continuous staff session: read master data, perform every stock operation, and be
    blocked from every admin-only action along the way - proving the role boundary holds across
    a realistic sequence, not just in isolated single-request tests."""
    product = client.post(
        "/products",
        json={"sku": "CMP-SSD-1TB", "name": "1TB NVMe SSD", "category_id": category_id, "unit_price": "79.99"},
        headers=admin_headers,
    ).json()

    assert client.get("/products", headers=staff_headers).status_code == 200
    assert client.get("/warehouses", headers=staff_headers).status_code == 200
    assert client.get("/categories", headers=staff_headers).status_code == 200

    assert (
        client.post(
            "/stock/in",
            json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 60},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/transfer",
            json={
                "product_id": product["id"],
                "from_warehouse_id": warehouse_a_id,
                "to_warehouse_id": warehouse_b_id,
                "quantity": 20,
            },
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/stock/out",
            json={"product_id": product["id"], "warehouse_id": warehouse_b_id, "quantity": 5},
            headers=staff_headers,
        ).status_code
        == 201
    )
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == 40
    assert _quantity_at(client, admin_headers, product["id"], warehouse_b_id) == 15

    assert (
        client.post(
            "/products",
            json={"sku": "X", "name": "X", "category_id": category_id, "unit_price": "1.00"},
            headers=staff_headers,
        ).status_code
        == 403
    )
    assert (
        client.patch(f"/products/{product['id']}", json={"unit_price": "1.00"}, headers=staff_headers).status_code
        == 403
    )
    assert client.delete(f"/products/{product['id']}", headers=staff_headers).status_code == 403
    assert client.post("/warehouses", json={"name": "New WH"}, headers=staff_headers).status_code == 403
    assert client.get("/users", headers=staff_headers).status_code == 403


def test_admin_lifecycle_flow(client, admin_headers, admin_user, db_session):
    """Register a new user, promote them to admin, have them exercise admin-only endpoints, demote
    the original admin back to staff (now safe with two admins), and confirm the last-admin guard
    fires again once back down to one."""
    from app.security import create_access_token

    register_response = client.post(
        "/auth/register",
        json={"email": "promoted@example.com", "password": SAMPLE_PASSWORD, "full_name": "Promoted User"},
    )
    new_user_id = register_response.json()["id"]
    assert register_response.json()["role"] == "staff"

    promote_response = client.patch(f"/users/{new_user_id}", json={"role": "admin"}, headers=admin_headers)
    assert promote_response.status_code == 200
    assert promote_response.json()["role"] == "admin"

    new_admin_headers = {"Authorization": f"Bearer {create_access_token(new_user_id)}"}
    assert client.get("/users", headers=new_admin_headers).status_code == 200
    assert (
        client.post("/categories", json={"name": "Promoted-Created"}, headers=new_admin_headers).status_code == 201
    )

    demote_original = client.patch(f"/users/{admin_user.id}", json={"role": "staff"}, headers=new_admin_headers)
    assert demote_original.status_code == 200

    guard_response = client.patch(f"/users/{new_user_id}", json={"role": "staff"}, headers=new_admin_headers)
    assert guard_response.status_code == 409
    assert guard_response.json()["detail"] == Messages.LAST_ADMIN_GUARD


def test_product_lifecycle_flow(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    """Create, stock at two warehouses, edit, soft-delete, confirm it's rejected from new stock
    operations afterward, and confirm its historical movements remain intact and correctly
    attributed despite the product no longer being active."""
    product = client.post(
        "/products",
        json={
            "sku": "PRF-KB-MECH",
            "name": "Mechanical Keyboard",
            "category_id": category_id,
            "unit_price": "69.00",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()

    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 25},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_b_id, "quantity": 10},
        headers=admin_headers,
    )

    updated = client.patch(f"/products/{product['id']}", json={"unit_price": "59.00"}, headers=admin_headers)
    assert updated.status_code == 200
    assert updated.json()["unit_price"] == "59.00"

    assert client.delete(f"/products/{product['id']}", headers=admin_headers).status_code == 204

    rejected = client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    assert rejected.status_code == 404

    # existing stock and the historical ledger both survive the soft-delete untouched
    assert _quantity_at(client, admin_headers, product["id"], warehouse_a_id) == 25
    assert _quantity_at(client, admin_headers, product["id"], warehouse_b_id) == 10
    movements = client.get(f"/stock/movements?product_id={product['id']}", headers=admin_headers).json()["items"]
    assert len(movements) == 2
    assert all(m["product"]["id"] == product["id"] for m in movements)


def test_low_stock_alert_lifecycle_flow(client, admin_headers, category_id, warehouse_a_id):
    """Stock drops to the threshold and the item appears in the low-stock view; restocking above
    the threshold makes it disappear again."""
    product = client.post(
        "/products",
        json={
            "sku": "NET-SW-8P",
            "name": "8-Port Switch",
            "category_id": category_id,
            "unit_price": "39.00",
            "min_stock_threshold": LOW_STOCK_THRESHOLD,
        },
        headers=admin_headers,
    ).json()

    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": LOW_STOCK_THRESHOLD + 10},
        headers=admin_headers,
    )
    low_stock_ids = {
        item["product"]["id"] for item in client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    }
    assert product["id"] not in low_stock_ids

    client.post(
        "/stock/out",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    low_stock_ids = {
        item["product"]["id"] for item in client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    }
    assert product["id"] in low_stock_ids

    client.post(
        "/stock/in",
        json={"product_id": product["id"], "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    low_stock_ids = {
        item["product"]["id"] for item in client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    }
    assert product["id"] not in low_stock_ids
