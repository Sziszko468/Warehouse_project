from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.schemas.common import ProductBrief, WarehouseBrief


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product: ProductBrief
    warehouse: WarehouseBrief
    quantity: int
    reserved_quantity: int
    updated_at: datetime

    @computed_field
    @property
    def available_quantity(self) -> int:
        return self.quantity - self.reserved_quantity


class LowStockRead(StockRead):
    min_stock_threshold: int
