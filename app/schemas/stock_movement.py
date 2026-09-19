from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.stock_movement import MovementType
from app.schemas.common import ProductBrief, UserBrief, WarehouseBrief


class StockInCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    note: str | None = None


class StockOutCreate(BaseModel):
    product_id: int
    warehouse_id: int
    quantity: int = Field(gt=0)
    note: str | None = None


class StockTransferCreate(BaseModel):
    product_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    quantity: int = Field(gt=0)
    note: str | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    movement_type: MovementType
    quantity: int
    from_warehouse: WarehouseBrief | None
    to_warehouse: WarehouseBrief | None
    note: str | None
    performed_by: UserBrief
    created_at: datetime
