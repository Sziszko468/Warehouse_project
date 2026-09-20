from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import CategoryBrief, CustomerBrief, SupplierBrief, WarehouseBrief


class StockValuationByWarehouse(BaseModel):
    warehouse: WarehouseBrief
    total_quantity: int
    total_value: Decimal


class StockValuationByCategory(BaseModel):
    category: CategoryBrief
    total_quantity: int
    total_value: Decimal


class StockValuationReport(BaseModel):
    total_quantity: int
    total_value: Decimal
    by_warehouse: list[StockValuationByWarehouse]
    by_category: list[StockValuationByCategory]


class PurchaseActivityRow(BaseModel):
    supplier: SupplierBrief
    orders_submitted: int
    orders_received: int
    received_value: Decimal


class SalesFulfillmentActivityRow(BaseModel):
    customer: CustomerBrief
    orders_confirmed: int
    shipments_created: int
    shipped_value: Decimal
