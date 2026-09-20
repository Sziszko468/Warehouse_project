from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import category as crud_category
from app.database import get_db
from app.dependencies import PaginationParams, get_current_user, require_admin
from app.messages import Messages
from app.models.category import Category
from app.models.user import User
from app.routers.helpers import get_or_404
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Page[CategoryRead])
def list_categories(
    include_inactive: bool = False,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Page[CategoryRead]:
    items, total = crud_category.list_categories(
        db, include_inactive=include_inactive, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Category:
    return get_or_404(crud_category.get, db, category_id, Messages.CATEGORY_NOT_FOUND)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Category:
    if crud_category.get_by_name(db, payload.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=Messages.CATEGORY_NAME_EXISTS)
    return crud_category.create(db, payload)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> Category:
    category = get_or_404(crud_category.get, db, category_id, Messages.CATEGORY_NOT_FOUND)
    if payload.name and payload.name != category.name and crud_category.get_by_name(db, payload.name) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=Messages.CATEGORY_NAME_EXISTS)
    return crud_category.update(db, category, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> None:
    category = get_or_404(crud_category.get, db, category_id, Messages.CATEGORY_NOT_FOUND)
    crud_category.soft_delete(db, category)
