from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.purchase_order import PurchaseOrderStatus
from app.schemas.common import ProductBrief, SupplierBrief, UserBrief, WarehouseBrief


class PurchaseOrderLineCreate(BaseModel):
    product_id: int
    quantity_ordered: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    quantity_ordered: int
    quantity_received: int
    unit_price: Decimal


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1)


class PurchaseOrderUpdate(BaseModel):
    notes: str | None = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier: SupplierBrief
    warehouse: WarehouseBrief
    status: PurchaseOrderStatus
    notes: str | None
    created_by: UserBrief
    lines: list[PurchaseOrderLineRead]
    submitted_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PurchaseOrderReceiveLine(BaseModel):
    purchase_order_line_id: int
    quantity: int = Field(gt=0)


class PurchaseOrderReceiveRequest(BaseModel):
    lines: list[PurchaseOrderReceiveLine] = Field(min_length=1)
    note: str | None = None
