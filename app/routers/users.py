from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.database import get_db
from app.dependencies import PaginationParams, require_admin
from app.models.user import User, UserRole
from app.schemas.common import Page
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Page[UserRead])
def list_users(
    role: UserRole | None = None,
    is_active: bool | None = None,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Page[UserRead]:
    items, total = crud_user.list_users(
        db, role=role, is_active=is_active, limit=pagination.limit, offset=pagination.offset
    )
    return Page(items=items, total=total, limit=pagination.limit, offset=pagination.offset)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role == UserRole.ADMIN:
        losing_admin_status = (payload.role is not None and payload.role != UserRole.ADMIN) or (
            payload.is_active is False
        )
        if losing_admin_status and crud_user.count_active_admins(db, exclude_user_id=user.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote or deactivate the last active admin",
            )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.flush()
    db.refresh(user)
    return user
