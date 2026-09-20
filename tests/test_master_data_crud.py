"""Shared HTTP behavior for every "master data" resource (categories/suppliers/warehouses/
products): permissions, 404s, soft-delete lifecycle, pagination, partial update, uniqueness.
Parametrized over tests/resource_specs.py instead of one near-duplicate file per resource -
mirrors the same generalization the app layer itself uses (app/crud/common.py).

Anything genuinely resource-specific (product search/filters, price validation, soft-deleted-FK
rejection) lives in test_products.py instead.
"""

import pytest

from tests.constants import PAGE_LIMIT_MAX
from tests.resource_specs import ALL_SPECS, SUPPLIER, UNIQUE_NAME_SPECS, spec_id

# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_unauthenticated_rejected_on_list(client, spec):
    assert client.get(spec.endpoint).status_code == 401


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_unauthenticated_rejected_on_get(client, spec):
    assert client.get(f"{spec.endpoint}/1").status_code == 401


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_unauthenticated_rejected_on_create(client, spec):
    assert client.post(spec.endpoint, json={}).status_code == 401


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_unauthenticated_rejected_on_update(client, spec):
    assert client.patch(f"{spec.endpoint}/1", json={}).status_code == 401


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_unauthenticated_rejected_on_delete(client, spec):
    assert client.delete(f"{spec.endpoint}/1").status_code == 401


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_staff_can_list(client, staff_headers, spec):
    assert client.get(spec.endpoint, headers=staff_headers).status_code == 200


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_staff_can_get(client, admin_headers, staff_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    )
    response = client.get(f"{spec.endpoint}/{created.json()['id']}", headers=staff_headers)
    assert response.status_code == 200


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_staff_cannot_create(client, admin_headers, staff_headers, spec):
    payload = spec.build_create_payload(client, admin_headers)
    assert client.post(spec.endpoint, json=payload, headers=staff_headers).status_code == 403


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_staff_cannot_update(client, admin_headers, staff_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    )
    response = client.patch(
        f"{spec.endpoint}/{created.json()['id']}", json={spec.patch_field: spec.patch_value}, headers=staff_headers
    )
    assert response.status_code == 403


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_staff_cannot_delete(client, admin_headers, staff_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    )
    assert client.delete(f"{spec.endpoint}/{created.json()['id']}", headers=staff_headers).status_code == 403


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_admin_create_roundtrip(client, admin_headers, spec):
    payload = spec.build_create_payload(client, admin_headers)
    response = client.post(spec.endpoint, json=payload, headers=admin_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["is_active"] is True
    for key, value in payload.items():
        assert body[key] == value


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_get_nonexistent_404(client, admin_headers, spec):
    response = client.get(f"{spec.endpoint}/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == spec.not_found_message


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_update_nonexistent_404(client, admin_headers, spec):
    response = client.patch(
        f"{spec.endpoint}/999999", json={spec.patch_field: spec.patch_value}, headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == spec.not_found_message


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_delete_nonexistent_404(client, admin_headers, spec):
    response = client.delete(f"{spec.endpoint}/999999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == spec.not_found_message


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_partial_update_only_changes_given_field(client, admin_headers, spec):
    payload = spec.build_create_payload(client, admin_headers)
    created = client.post(spec.endpoint, json=payload, headers=admin_headers).json()

    response = client.patch(
        f"{spec.endpoint}/{created['id']}", json={spec.patch_field: spec.patch_value}, headers=admin_headers
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated[spec.patch_field] == spec.patch_value
    for key, value in payload.items():
        if key != spec.patch_field:
            assert updated[key] == value


# ---------------------------------------------------------------------------
# Soft delete lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_soft_delete_lifecycle(client, admin_headers, spec):
    created = client.post(
        spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers
    )
    resource_id = created.json()["id"]

    assert client.delete(f"{spec.endpoint}/{resource_id}", headers=admin_headers).status_code == 204

    default_list = client.get(spec.endpoint, headers=admin_headers).json()
    assert all(item["id"] != resource_id for item in default_list["items"])

    inclusive_list = client.get(f"{spec.endpoint}?include_inactive=true", headers=admin_headers).json()
    assert any(item["id"] == resource_id for item in inclusive_list["items"])

    reactivate = client.patch(f"{spec.endpoint}/{resource_id}", json={"is_active": True}, headers=admin_headers)
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True

    default_list_after = client.get(spec.endpoint, headers=admin_headers).json()
    assert any(item["id"] == resource_id for item in default_list_after["items"])


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_pagination_limit_one_returns_single_item(client, admin_headers, spec):
    for _ in range(3):
        client.post(spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers)
    response = client.get(f"{spec.endpoint}?limit=1", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["limit"] == 1


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_pagination_limit_at_max_accepted(client, admin_headers, spec):
    assert client.get(f"{spec.endpoint}?limit={PAGE_LIMIT_MAX}", headers=admin_headers).status_code == 200


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_pagination_limit_over_max_rejected(client, admin_headers, spec):
    assert client.get(f"{spec.endpoint}?limit={PAGE_LIMIT_MAX + 1}", headers=admin_headers).status_code == 422


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_pagination_negative_offset_rejected(client, admin_headers, spec):
    assert client.get(f"{spec.endpoint}?offset=-1", headers=admin_headers).status_code == 422


@pytest.mark.parametrize("spec", ALL_SPECS, ids=spec_id)
def test_pagination_offset_past_end_returns_empty(client, admin_headers, spec):
    client.post(spec.endpoint, json=spec.build_create_payload(client, admin_headers), headers=admin_headers)
    response = client.get(f"{spec.endpoint}?offset=999999", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["items"] == []


# ---------------------------------------------------------------------------
# Validation & uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "spec,missing_field",
    [(spec, required_field) for spec in ALL_SPECS for required_field in spec.required_fields],
    ids=[f"{spec.name}-missing-{required_field}" for spec in ALL_SPECS for required_field in spec.required_fields],
)
def test_create_missing_required_field_rejected(client, admin_headers, spec, missing_field):
    payload = spec.build_create_payload(client, admin_headers)
    del payload[missing_field]
    assert client.post(spec.endpoint, json=payload, headers=admin_headers).status_code == 422


@pytest.mark.parametrize("spec", UNIQUE_NAME_SPECS, ids=spec_id)
def test_duplicate_unique_field_rejected(client, admin_headers, spec):
    shared_value = f"Duplicate value for {spec.name}"
    first = spec.build_create_payload(client, admin_headers, unique_value=shared_value)
    assert client.post(spec.endpoint, json=first, headers=admin_headers).status_code == 201

    second = spec.build_create_payload(client, admin_headers, unique_value=shared_value)
    response = client.post(spec.endpoint, json=second, headers=admin_headers)
    assert response.status_code == 409
    assert response.json()["detail"] == spec.duplicate_message


def test_supplier_names_need_not_be_unique(client, admin_headers):
    payload = SUPPLIER.build_create_payload(client, admin_headers, unique_value="Shared Supplier Name")
    first = client.post(SUPPLIER.endpoint, json=payload, headers=admin_headers)
    second = client.post(SUPPLIER.endpoint, json=payload, headers=admin_headers)
    assert first.status_code == 201
    assert second.status_code == 201
