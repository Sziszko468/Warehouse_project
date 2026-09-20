from datetime import UTC, datetime, timedelta

from tests.constants import SAMPLE_UNIT_PRICE

# "+00:00" in an un-encoded query string is ambiguous (a literal "+" there means "space" to most
# URL parsers) - naive-looking ISO strings sidestep that entirely and FastAPI parses them fine.
FAR_FUTURE = (datetime.now(UTC) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")
FAR_PAST = (datetime.now(UTC) - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S")


def _stock_in(client, admin_headers, product_id, warehouse_id, quantity):
    return client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_id, "quantity": quantity},
        headers=admin_headers,
    )


# ---------------------------------------------------------------------------
# Stock valuation
# ---------------------------------------------------------------------------


def test_stock_valuation_matches_manual_sum(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product_a = client.post(
        "/products",
        json={"sku": "RPT-A", "name": "Report Product A", "category_id": category_id, "unit_price": "10.00"},
        headers=admin_headers,
    ).json()
    product_b = client.post(
        "/products",
        json={"sku": "RPT-B", "name": "Report Product B", "category_id": category_id, "unit_price": "2.50"},
        headers=admin_headers,
    ).json()
    _stock_in(client, admin_headers, product_a["id"], warehouse_a_id, 5)  # 50.00
    _stock_in(client, admin_headers, product_b["id"], warehouse_b_id, 4)  # 10.00

    report = client.get("/reports/stock-valuation", headers=admin_headers).json()

    warehouse_a_row = next(row for row in report["by_warehouse"] if row["warehouse"]["id"] == warehouse_a_id)
    warehouse_b_row = next(row for row in report["by_warehouse"] if row["warehouse"]["id"] == warehouse_b_id)
    assert warehouse_a_row["total_value"] == "50.00"
    assert warehouse_a_row["total_quantity"] == 5
    assert warehouse_b_row["total_value"] == "10.00"
    assert warehouse_b_row["total_quantity"] == 4

    category_row = next(row for row in report["by_category"] if row["category"]["id"] == category_id)
    assert category_row["total_quantity"] == 9
    assert category_row["total_value"] == "60.00"


def test_stock_valuation_filter_by_warehouse(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product = client.post(
        "/products",
        json={"sku": "RPT-C", "name": "Report Product C", "category_id": category_id, "unit_price": "3.00"},
        headers=admin_headers,
    ).json()
    _stock_in(client, admin_headers, product["id"], warehouse_a_id, 10)
    _stock_in(client, admin_headers, product["id"], warehouse_b_id, 100)

    report = client.get(f"/reports/stock-valuation?warehouse_id={warehouse_a_id}", headers=admin_headers).json()
    assert len(report["by_warehouse"]) == 1
    assert report["by_warehouse"][0]["warehouse"]["id"] == warehouse_a_id
    assert report["by_warehouse"][0]["total_quantity"] == 10


# ---------------------------------------------------------------------------
# Purchase activity
# ---------------------------------------------------------------------------


def test_purchase_activity_counts_and_value(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 10, "unit_price": "4.00"}],
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

    report = client.get("/reports/purchase-activity", headers=admin_headers).json()
    row = next(r for r in report if r["supplier"]["id"] == supplier_id)
    assert row["orders_submitted"] == 1
    assert row["orders_received"] == 1
    assert row["received_value"] == "40.00"


def test_purchase_activity_excludes_out_of_range(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5, "unit_price": "1.00"}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)

    # a date range entirely in the future must exclude the submission that just happened
    report = client.get(f"/reports/purchase-activity?date_from={FAR_FUTURE}", headers=admin_headers).json()
    matching = [r for r in report if r["supplier"]["id"] == supplier_id]
    assert matching == []

    # a date range entirely in the past must also exclude it
    report_past = client.get(f"/reports/purchase-activity?date_to={FAR_PAST}", headers=admin_headers).json()
    matching_past = [r for r in report_past if r["supplier"]["id"] == supplier_id]
    assert matching_past == []


# ---------------------------------------------------------------------------
# Sales / fulfillment activity
# ---------------------------------------------------------------------------


def test_sales_fulfillment_activity_counts_and_value(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 20)
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
    line_id = order["lines"][0]["id"]
    client.post(
        "/shipments",
        json={"customer_order_id": order["id"], "lines": [{"customer_order_line_id": line_id, "quantity": 10}]},
        headers=admin_headers,
    )

    report = client.get("/reports/sales-fulfillment-activity", headers=admin_headers).json()
    row = next(r for r in report if r["customer"]["id"] == customer_id)
    assert row["orders_confirmed"] == 1
    assert row["shipments_created"] == 1
    assert float(row["shipped_value"]) == 10 * float(SAMPLE_UNIT_PRICE)


def test_sales_fulfillment_activity_excludes_out_of_range(
    client, admin_headers, customer_id, warehouse_a_id, product_id
):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 10)
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

    report = client.get(
        f"/reports/sales-fulfillment-activity?date_from={FAR_FUTURE}", headers=admin_headers
    ).json()
    matching = [r for r in report if r["customer"]["id"] == customer_id]
    assert matching == []


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


def test_staff_can_view_reports(client, staff_headers):
    assert client.get("/reports/stock-valuation", headers=staff_headers).status_code == 200
    assert client.get("/reports/purchase-activity", headers=staff_headers).status_code == 200
    assert client.get("/reports/sales-fulfillment-activity", headers=staff_headers).status_code == 200


def test_unauthenticated_rejected(client):
    assert client.get("/reports/stock-valuation").status_code == 401
    assert client.get("/reports/purchase-activity").status_code == 401
    assert client.get("/reports/sales-fulfillment-activity").status_code == 401
