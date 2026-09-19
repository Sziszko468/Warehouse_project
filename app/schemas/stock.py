from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ProductBrief, WarehouseBrief


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    warehouse: WarehouseBrief
    quantity: int
    updated_at: datetime


class LowStockRead(StockRead):
    min_stock_threshold: int
