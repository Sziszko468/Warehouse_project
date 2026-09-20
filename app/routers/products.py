from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import category as crud_category
from app.crud import product as crud_product
from app.crud import supplier as crud_supplier
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.product import Product
from app.models.user import User
from app.routers.csv_helpers import EXPORT_ROW_LIMIT, csv_response
from app.routers.helpers import get_or_404
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _validate_references(db: Session, *, category_id: int | None, supplier_id: int | None) -> None:
    # A soft-deleted category/supplier counts as "not found" for assigning to a product - it's
    # hidden from every normal list/select, so a product left pointing at one would be silently
    # orphaned from the admin's perspective (see the 404 convention in the project plan).
    if category_id is not None:
        category = crud_category.get(db, category_id)
        if category is None or not category.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Messages.CATEGORY_NOT_FOUND)
    if supplier_id is not None:
        supplier = crud_supplier.get(db, supplier_id)
        if supplier is None or not supplier.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Messages.SUPPLIER_NOT_FOUND)


@router.get("", response_model=Page[ProductRead])
def list_products(
    include_inactive: bool = False,
    category_id: int | None = None,
    supplier_id: int | None = None,
    search: str | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[ProductRead]:
    items, total = crud_product.list_products(
        db,
        include_inactive=include_inactive,
        category_id=category_id,
        supplier_id=supplier_id,
        search=search,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/export")
def export_products(
    include_inactive: bool = False,
    category_id: int | None = None,
    supplier_id: int | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items, _total = crud_product.list_products(
        db,
        include_inactive=include_inactive,
        category_id=category_id,
        supplier_id=supplier_id,
        search=search,
        limit=EXPORT_ROW_LIMIT,
        offset=0,
    )
    rows = [
        [
            p.id,
            p.sku,
            p.name,
            p.description or "",
            p.category_id,
            p.supplier_id or "",
            p.unit_price,
            p.min_stock_threshold,
            p.is_active,
        ]
        for p in items
    ]
    return csv_response(
        "products.csv",
        [
            "id",
            "sku",
            "name",
            "description",
            "category_id",
            "supplier_id",
            "unit_price",
            "min_stock_threshold",
            "is_active",
        ],
        rows,
    )


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Product:
    return get_or_404(crud_product.get, db, product_id, Messages.PRODUCT_NOT_FOUND)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> Product:
    if crud_product.get_by_sku(db, payload.sku) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=Messages.SKU_ALREADY_EXISTS)
    _validate_references(db, category_id=payload.category_id, supplier_id=payload.supplier_id)
    return crud_product.create(db, payload, performed_by_id=current_user.id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> Product:
    product = get_or_404(crud_product.get, db, product_id, Messages.PRODUCT_NOT_FOUND)
    if payload.sku and payload.sku != product.sku and crud_product.get_by_sku(db, payload.sku) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=Messages.SKU_ALREADY_EXISTS)
    _validate_references(db, category_id=payload.category_id, supplier_id=payload.supplier_id)
    return crud_product.update(db, product, payload, performed_by_id=current_user.id)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
) -> None:
    product = get_or_404(crud_product.get, db, product_id, Messages.PRODUCT_NOT_FOUND)
    crud_product.soft_delete(db, product, performed_by_id=current_user.id)
