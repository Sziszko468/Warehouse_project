from datetime import UTC, datetime, timedelta

import pytest

from tests.constants import LOW_STOCK_THRESHOLD, PAGE_LIMIT_MAX, PAGE_LIMIT_SMALL, ZERO_THRESHOLD

# category_id, warehouse_a_id, warehouse_b_id are shared fixtures from conftest.py


def _make_product(client, admin_headers, category_id, sku, threshold):
    payload = {
        "sku": sku,
        "name": sku,
        "category_id": category_id,
        "unit_price": "1.00",
        "min_stock_threshold": threshold,
    }
    return client.post("/products", json=payload, headers=admin_headers).json()["id"]


def test_low_stock_only_returns_items_at_or_below_threshold(client, admin_headers, category_id, warehouse_a_id):
    low_product = _make_product(client, admin_headers, category_id, "LOW-1", threshold=LOW_STOCK_THRESHOLD)
    ok_product = _make_product(client, admin_headers, category_id, "OK-1", threshold=LOW_STOCK_THRESHOLD)

    client.post(
        "/stock/in",
        json={"product_id": low_product, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": ok_product, "warehouse_id": warehouse_a_id, "quantity": 50},
        headers=admin_headers,
    )

    response = client.get("/stock/low-stock", headers=admin_headers)
    assert response.status_code == 200
    product_ids = {item["product"]["id"] for item in response.json()["items"]}
    assert low_product in product_ids
    assert ok_product not in product_ids


def test_low_stock_at_exact_threshold_is_included(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "EXACT-1", threshold=LOW_STOCK_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": LOW_STOCK_THRESHOLD},
        headers=admin_headers,
    )

    items = client.get("/stock/low-stock", headers=admin_headers).json()["items"]
    assert any(item["product"]["id"] == product_id for item in items)


def test_movements_filter_by_product(client, admin_headers, category_id, warehouse_a_id):
    product_a = _make_product(client, admin_headers, category_id, "MOVE-A", threshold=ZERO_THRESHOLD)
    product_b = _make_product(client, admin_headers, category_id, "MOVE-B", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_a, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_b, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )

    items = client.get(f"/stock/movements?product_id={product_a}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["product"]["id"] == product_a


def test_movements_filter_by_type(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product_id = _make_product(client, admin_headers, category_id, "TYPE-1", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 5,
        },
        headers=admin_headers,
    )

    items = client.get("/stock/movements?movement_type=out", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["movement_type"] == "out"


def test_movements_pagination(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "PAGE-1", threshold=ZERO_THRESHOLD)
    for _ in range(5):
        client.post(
            "/stock/in",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
            headers=admin_headers,
        )

    page1 = client.get(f"/stock/movements?limit={PAGE_LIMIT_SMALL}&offset=0", headers=admin_headers).json()
    page2 = client.get(
        f"/stock/movements?limit={PAGE_LIMIT_SMALL}&offset={PAGE_LIMIT_SMALL}", headers=admin_headers
    ).json()
    assert len(page1["items"]) == PAGE_LIMIT_SMALL
    assert len(page2["items"]) == PAGE_LIMIT_SMALL
    assert page1["total"] == 5
    assert {item["id"] for item in page1["items"]}.isdisjoint({item["id"] for item in page2["items"]})


@pytest.mark.parametrize("movement_type", ["in", "out", "transfer"])
def test_movements_filter_by_each_type(
    client, admin_headers, category_id, warehouse_a_id, warehouse_b_id, movement_type
):
    product_id = _make_product(
        client, admin_headers, category_id, f"MTYPE-{movement_type}", threshold=ZERO_THRESHOLD
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    client.post(
        "/stock/out",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 5,
        },
        headers=admin_headers,
    )

    items = client.get(
        f"/stock/movements?product_id={product_id}&movement_type={movement_type}", headers=admin_headers
    ).json()["items"]
    assert len(items) == 1
    assert items[0]["movement_type"] == movement_type


def test_movements_filter_by_warehouse_matches_from_or_to(
    client, admin_headers, category_id, warehouse_a_id, warehouse_b_id
):
    product_id = _make_product(client, admin_headers, category_id, "WH-FILTER", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 20},
        headers=admin_headers,
    )
    client.post(
        "/stock/transfer",
        json={
            "product_id": product_id,
            "from_warehouse_id": warehouse_a_id,
            "to_warehouse_id": warehouse_b_id,
            "quantity": 5,
        },
        headers=admin_headers,
    )

    # warehouse_b only ever appears as the "to" side of the transfer - must still be found
    items = client.get(f"/stock/movements?warehouse_id={warehouse_b_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["movement_type"] == "transfer"


def test_movements_filter_by_performed_by(client, admin_headers, staff_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "PERF-1", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=staff_headers,
    )

    staff_id = client.get("/auth/me", headers=staff_headers).json()["id"]
    items = client.get(f"/stock/movements?performed_by_id={staff_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["performed_by"]["id"] == staff_id


def test_movements_filter_by_date_from_excludes_future_only_data(
    client, admin_headers, category_id, warehouse_a_id
):
    product_id = _make_product(client, admin_headers, category_id, "DATE-1", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )

    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    # the "+00:00" UTC offset must go through query-param encoding (params=), not a raw f-string -
    # embedded directly in the URL, "+" is read back as a space by the server and 422s.
    items = client.get("/stock/movements", params={"date_from": future}, headers=admin_headers).json()["items"]
    assert items == []


def test_movements_filter_by_date_from_includes_past_data(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "DATE-2", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )

    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    items = client.get("/stock/movements", params={"date_from": past}, headers=admin_headers).json()["items"]
    assert any(item["product"]["id"] == product_id for item in items)


def test_movements_filter_by_date_to_excludes_past_only_data(client, admin_headers, category_id, warehouse_a_id):
    product_id = _make_product(client, admin_headers, category_id, "DATE-3", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )

    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    items = client.get("/stock/movements", params={"date_to": yesterday}, headers=admin_headers).json()["items"]
    assert items == []


def test_movements_combined_filters(client, admin_headers, category_id, warehouse_a_id):
    product_a = _make_product(client, admin_headers, category_id, "COMBO-A", threshold=ZERO_THRESHOLD)
    product_b = _make_product(client, admin_headers, category_id, "COMBO-B", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_a, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )
    client.post(
        "/stock/out",
        json={"product_id": product_a, "warehouse_id": warehouse_a_id, "quantity": 5},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_b, "warehouse_id": warehouse_a_id, "quantity": 10},
        headers=admin_headers,
    )

    items = client.get(f"/stock/movements?product_id={product_a}&movement_type=out", headers=admin_headers).json()[
        "items"
    ]
    assert len(items) == 1
    assert items[0]["product"]["id"] == product_a
    assert items[0]["movement_type"] == "out"


def test_low_stock_filter_by_warehouse(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product_id = _make_product(client, admin_headers, category_id, "LOWWH-1", threshold=LOW_STOCK_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_b_id, "quantity": 1},
        headers=admin_headers,
    )

    items = client.get(f"/stock/low-stock?warehouse_id={warehouse_a_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["warehouse"]["id"] == warehouse_a_id


def test_low_stock_pagination(client, admin_headers, category_id, warehouse_a_id):
    for i in range(3):
        product_id = _make_product(
            client, admin_headers, category_id, f"LOWPAGE-{i}", threshold=LOW_STOCK_THRESHOLD
        )
        client.post(
            "/stock/in",
            json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
            headers=admin_headers,
        )

    body = client.get(f"/stock/low-stock?limit={PAGE_LIMIT_SMALL}", headers=admin_headers).json()
    assert len(body["items"]) == PAGE_LIMIT_SMALL
    assert body["total"] == 3


def test_stock_levels_filter_by_product(client, admin_headers, category_id, warehouse_a_id):
    product_a = _make_product(client, admin_headers, category_id, "LEVEL-A", threshold=ZERO_THRESHOLD)
    product_b = _make_product(client, admin_headers, category_id, "LEVEL-B", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_a, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_b, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )

    items = client.get(f"/stock?product_id={product_a}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["product"]["id"] == product_a


def test_stock_levels_filter_by_warehouse(client, admin_headers, category_id, warehouse_a_id, warehouse_b_id):
    product_id = _make_product(client, admin_headers, category_id, "LEVELWH-1", threshold=ZERO_THRESHOLD)
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_a_id, "quantity": 1},
        headers=admin_headers,
    )
    client.post(
        "/stock/in",
        json={"product_id": product_id, "warehouse_id": warehouse_b_id, "quantity": 1},
        headers=admin_headers,
    )

    items = client.get(f"/stock?warehouse_id={warehouse_a_id}", headers=admin_headers).json()["items"]
    assert len(items) == 1
    assert items[0]["warehouse"]["id"] == warehouse_a_id


def test_stock_levels_pagination_limit_over_max_rejected(client, admin_headers):
    response = client.get(f"/stock?limit={PAGE_LIMIT_MAX + 1}", headers=admin_headers)
    assert response.status_code == 422


def test_unauthenticated_rejected_on_stock_queries(client):
    assert client.get("/stock").status_code == 401
    assert client.get("/stock/low-stock").status_code == 401
    assert client.get("/stock/movements").status_code == 401
