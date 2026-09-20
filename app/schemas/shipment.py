from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.shipment import ShipmentStatus
from app.schemas.common import ProductBrief, UserBrief


class ShipmentLineCreate(BaseModel):
    customer_order_line_id: int
    quantity: int = Field(gt=0)


class ShipmentLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    quantity: int


class ShipmentCreate(BaseModel):
    customer_order_id: int
    carrier: str | None = None
    tracking_number: str | None = None
    lines: list[ShipmentLineCreate] = Field(min_length=1)


class ShipmentUpdate(BaseModel):
    carrier: str | None = None
    tracking_number: str | None = None


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_order_id: int
    carrier: str | None
    tracking_number: str | None
    status: ShipmentStatus
    lines: list[ShipmentLineRead]
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_by: UserBrief
    created_at: datetime
    updated_at: datetime
