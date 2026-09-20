import csv
import io


def _parse_csv(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def _stock_in(client, admin_headers, product_id, warehouse_id, quantity):
    return client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_id, "quantity": quantity},
        headers=admin_headers,
    )


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


def test_export_products(client, admin_headers, category_id):
    client.post(
        "/products",
        json={"sku": "CSV-1", "name": "CSV Product", "category_id": category_id, "unit_price": "1.00"},
        headers=admin_headers,
    )

    response = client.get("/products/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]

    rows = _parse_csv(response.text)
    assert rows[0] == [
        "id",
        "sku",
        "name",
        "description",
        "category_id",
        "supplier_id",
        "unit_price",
        "min_stock_threshold",
        "is_active",
    ]
    skus = [row[1] for row in rows[1:]]
    assert "CSV-1" in skus


def test_export_products_respects_filters(client, admin_headers, category_id, other_category_id):
    client.post(
        "/products",
        json={"sku": "CSV-A", "name": "In Category", "category_id": category_id, "unit_price": "1.00"},
        headers=admin_headers,
    )
    client.post(
        "/products",
        json={"sku": "CSV-B", "name": "Other Category", "category_id": other_category_id, "unit_price": "1.00"},
        headers=admin_headers,
    )

    response = client.get(f"/products/export?category_id={category_id}", headers=admin_headers)
    rows = _parse_csv(response.text)
    skus = [row[1] for row in rows[1:]]
    assert "CSV-A" in skus
    assert "CSV-B" not in skus


def test_export_products_unauthenticated_rejected(client):
    assert client.get("/products/export").status_code == 401


# ---------------------------------------------------------------------------
# Stock / movements
# ---------------------------------------------------------------------------


def test_export_stock(client, admin_headers, product_id, warehouse_a_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 15)

    response = client.get("/stock/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    rows = _parse_csv(response.text)
    assert rows[0][0] == "id"
    matching = [row for row in rows[1:] if row[1] == "SKU-1"]
    assert len(matching) == 1
    assert matching[0][4] == "15"  # quantity column


def test_export_movements(client, admin_headers, product_id, warehouse_a_id):
    _stock_in(client, admin_headers, product_id, warehouse_a_id, 7)

    response = client.get("/stock/movements/export", headers=admin_headers)
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    assert rows[0] == [
        "id",
        "created_at",
        "product_sku",
        "product_name",
        "movement_type",
        "quantity",
        "from_warehouse",
        "to_warehouse",
        "performed_by",
        "note",
    ]
    assert any(row[2] == "SKU-1" and row[4] == "in" and row[5] == "7" for row in rows[1:])


def test_export_stock_unauthenticated_rejected(client):
    assert client.get("/stock/export").status_code == 401
    assert client.get("/stock/movements/export").status_code == 401


# ---------------------------------------------------------------------------
# Purchase orders / customer orders
# ---------------------------------------------------------------------------


def test_export_purchase_orders(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5, "unit_price": "2.00"}],
        },
        headers=admin_headers,
    )

    response = client.get("/purchase-orders/export", headers=admin_headers)
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    assert rows[0][0] == "id"
    assert len(rows) == 2  # header + the one PO created above


def test_export_purchase_orders_filter_by_status(client, admin_headers, supplier_id, warehouse_a_id, product_id):
    po = client.post(
        "/purchase-orders",
        json={
            "supplier_id": supplier_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 5, "unit_price": "2.00"}],
        },
        headers=admin_headers,
    ).json()
    client.post(f"/purchase-orders/{po['id']}/submit", headers=admin_headers)

    draft_only = _parse_csv(client.get("/purchase-orders/export?status=draft", headers=admin_headers).text)
    assert len(draft_only) == 1  # header only, no rows

    submitted_only = _parse_csv(client.get("/purchase-orders/export?status=submitted", headers=admin_headers).text)
    assert len(submitted_only) == 2


def test_export_customer_orders(client, admin_headers, customer_id, warehouse_a_id, product_id):
    client.post(
        "/customer-orders",
        json={
            "customer_id": customer_id,
            "warehouse_id": warehouse_a_id,
            "lines": [{"product_id": product_id, "quantity_ordered": 3}],
        },
        headers=admin_headers,
    )

    response = client.get("/customer-orders/export", headers=admin_headers)
    assert response.status_code == 200
    rows = _parse_csv(response.text)
    assert rows[0][0] == "id"
    assert len(rows) == 2


def test_export_orders_unauthenticated_rejected(client):
    assert client.get("/purchase-orders/export").status_code == 401
    assert client.get("/customer-orders/export").status_code == 401
