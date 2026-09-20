"""One spec per "master data" resource (category/supplier/warehouse/product), so
test_master_data_crud.py can express the ~90%-identical behavior all four share (permissions,
404s, soft-delete lifecycle, pagination, partial update, uniqueness) as test functions
parametrized over this list, instead of one near-duplicate test file per resource.
"""

import itertools
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.messages import Messages
from tests.constants import SAMPLE_UNIT_PRICE

_counter = itertools.count(1)


def _next(prefix: str) -> str:
    return f"{prefix} {next(_counter)}"


@dataclass(frozen=True)
class ResourceSpec:
    name: str
    endpoint: str
    not_found_message: str
    required_fields: list[str]
    # field/value used to prove a PATCH only touches what it's given
    patch_field: str
    patch_value: Any
    # (client, admin_headers, unique_value=None) -> a valid create payload; a caller-supplied
    # unique_value forces the resource's unique field (name or sku) to that value, so duplicate-
    # conflict tests can create two payloads that collide on purpose.
    build_create_payload: Callable[..., dict]
    unique_field: str | None = None
    duplicate_message: str | None = None
    supports_duplicate_conflict: bool = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "supports_duplicate_conflict", self.unique_field is not None)


def _category_payload(client, admin_headers, unique_value: str | None = None) -> dict:
    return {"name": unique_value or _next("Category"), "description": "A test category"}


def _supplier_payload(client, admin_headers, unique_value: str | None = None) -> dict:
    # suppliers deliberately have no unique-name constraint (confirmed design, see
    # tests/test_master_data_crud.py's supplier duplicate-name test) - unique_value is accepted
    # for interface symmetry with the other specs but has no uniqueness meaning here.
    return {"name": unique_value or _next("Supplier"), "contact_name": "Test Contact"}


def _customer_payload(client, admin_headers, unique_value: str | None = None) -> dict:
    # customers deliberately have no unique-name constraint, mirroring suppliers - unique_value is
    # accepted for interface symmetry with the other specs but has no uniqueness meaning here.
    return {"name": unique_value or _next("Customer"), "contact_name": "Test Contact"}


def _warehouse_payload(client, admin_headers, unique_value: str | None = None) -> dict:
    return {"name": unique_value or _next("Warehouse"), "address": "1 Test St"}


def _product_payload(client, admin_headers, unique_value: str | None = None) -> dict:
    category_id = client.post(
        "/categories", json={"name": _next("ProductCategory")}, headers=admin_headers
    ).json()["id"]
    return {
        "sku": unique_value or _next("SKU"),
        "name": "Test Product",
        "category_id": category_id,
        "unit_price": SAMPLE_UNIT_PRICE,
        "min_stock_threshold": 0,
    }


CATEGORY = ResourceSpec(
    name="category",
    endpoint="/categories",
    not_found_message=Messages.CATEGORY_NOT_FOUND,
    required_fields=["name"],
    patch_field="description",
    patch_value="Updated description",
    build_create_payload=_category_payload,
    unique_field="name",
    duplicate_message=Messages.CATEGORY_NAME_EXISTS,
)

SUPPLIER = ResourceSpec(
    name="supplier",
    endpoint="/suppliers",
    not_found_message=Messages.SUPPLIER_NOT_FOUND,
    required_fields=["name"],
    patch_field="phone",
    patch_value="555-0100",
    build_create_payload=_supplier_payload,
    unique_field=None,
    duplicate_message=None,
)

CUSTOMER = ResourceSpec(
    name="customer",
    endpoint="/customers",
    not_found_message=Messages.CUSTOMER_NOT_FOUND,
    required_fields=["name"],
    patch_field="phone",
    patch_value="555-0100",
    build_create_payload=_customer_payload,
    unique_field=None,
    duplicate_message=None,
)

WAREHOUSE = ResourceSpec(
    name="warehouse",
    endpoint="/warehouses",
    not_found_message=Messages.WAREHOUSE_NOT_FOUND,
    required_fields=["name"],
    patch_field="address",
    patch_value="2 Updated Ave",
    build_create_payload=_warehouse_payload,
    unique_field="name",
    duplicate_message=Messages.WAREHOUSE_NAME_EXISTS,
)

PRODUCT = ResourceSpec(
    name="product",
    endpoint="/products",
    not_found_message=Messages.PRODUCT_NOT_FOUND,
    required_fields=["sku", "name", "category_id", "unit_price"],
    patch_field="unit_price",
    patch_value="19.99",
    build_create_payload=_product_payload,
    unique_field="sku",
    duplicate_message=Messages.SKU_ALREADY_EXISTS,
)

ALL_SPECS = [CATEGORY, SUPPLIER, CUSTOMER, WAREHOUSE, PRODUCT]
UNIQUE_NAME_SPECS = [spec for spec in ALL_SPECS if spec.supports_duplicate_conflict]


def spec_id(spec: ResourceSpec) -> str:
    return spec.name
