from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.customer_order import CustomerOrderStatus
from app.schemas.common import CustomerBrief, ProductBrief, UserBrief, WarehouseBrief


class CustomerOrderLineCreate(BaseModel):
    product_id: int
    quantity_ordered: int = Field(gt=0)


class CustomerOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    quantity_ordered: int
    quantity_shipped: int
    unit_price: Decimal


class CustomerOrderCreate(BaseModel):
    customer_id: int
    warehouse_id: int
    notes: str | None = None
    lines: list[CustomerOrderLineCreate] = Field(min_length=1)


class CustomerOrderUpdate(BaseModel):
    notes: str | None = None


class CustomerOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer: CustomerBrief
    warehouse: WarehouseBrief
    status: CustomerOrderStatus
    notes: str | None
    created_by: UserBrief
    lines: list[CustomerOrderLineRead]
    confirmed_at: datetime | None
    shipped_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
