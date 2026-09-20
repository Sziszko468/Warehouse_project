from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import user as crud_user
from app.database import get_db
from app.dependencies import PaginationParams, require_admin
from app.exceptions import LastAdminError
from app.messages import Messages
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Messages.USER_NOT_FOUND)
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=Messages.USER_NOT_FOUND)

    if user.role == UserRole.ADMIN:
        losing_admin_status = (payload.role is not None and payload.role != UserRole.ADMIN) or (
            payload.is_active is False
        )
        if losing_admin_status:
            # Locks every active admin row before counting, so a concurrent request demoting a
            # different admin can't race past this check using a stale count (see
            # crud_user.lock_active_admins).
            remaining_admins = [admin for admin in crud_user.lock_active_admins(db) if admin.id != user.id]
            if not remaining_admins:
                raise LastAdminError()

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.flush()
    db.refresh(user)
    return user
