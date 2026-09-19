from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import category as crud_category
from app.crud import product as crud_product
from app.crud import supplier as crud_supplier
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.models.product import Product
from app.models.user import User
from app.schemas.common import Page
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _validate_references(db: Session, *, category_id: int | None, supplier_id: int | None) -> None:
    if category_id is not None and crud_category.get(db, category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    if supplier_id is not None and crud_supplier.get(db, supplier_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")


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


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Product:
    product = crud_product.get(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Product:
    if crud_product.get_by_sku(db, payload.sku) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    _validate_references(db, category_id=payload.category_id, supplier_id=payload.supplier_id)
    return crud_product.create(db, payload)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Product:
    product = crud_product.get(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if payload.sku and payload.sku != product.sku and crud_product.get_by_sku(db, payload.sku) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")
    _validate_references(db, category_id=payload.category_id, supplier_id=payload.supplier_id)
    return crud_product.update(db, product, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> None:
    product = crud_product.get(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    crud_product.soft_delete(db, product)
