from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import report as crud_report
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.report import PurchaseActivityRow, SalesFulfillmentActivityRow, StockValuationReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/stock-valuation", response_model=StockValuationReport)
def stock_valuation(
    warehouse_id: int | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> StockValuationReport:
    return StockValuationReport(
        **crud_report.stock_valuation(db, warehouse_id=warehouse_id, category_id=category_id)
    )


@router.get("/purchase-activity", response_model=list[PurchaseActivityRow])
def purchase_activity(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PurchaseActivityRow]:
    rows = crud_report.purchase_activity(db, date_from=date_from, date_to=date_to)
    return [PurchaseActivityRow(**row) for row in rows]


@router.get("/sales-fulfillment-activity", response_model=list[SalesFulfillmentActivityRow])
def sales_fulfillment_activity(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SalesFulfillmentActivityRow]:
    rows = crud_report.sales_fulfillment_activity(db, date_from=date_from, date_to=date_to)
    return [SalesFulfillmentActivityRow(**row) for row in rows]
