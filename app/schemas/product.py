from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    sku: str
    name: str
    description: str | None = None
    category_id: int
    supplier_id: int | None = None
    unit_price: Decimal = Field(ge=0)
    min_stock_threshold: int = Field(default=0, ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: int | None = None
    supplier_id: int | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    min_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
