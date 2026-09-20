from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud.common import paginate
from app.models.user import User, UserRole
from app.security import hash_password


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(
    db: Session, *, email: str, password: str, full_name: str, role: UserRole = UserRole.STAFF
) -> User:
    user = User(email=email, hashed_password=hash_password(password), full_name=full_name, role=role)
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def count_active_admins(db: Session, *, exclude_user_id: int | None = None) -> int:
    stmt = select(func.count()).select_from(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    return db.scalar(stmt) or 0


def lock_active_admins(db: Session) -> list[User]:
    """Row-locks every currently active admin for the rest of this transaction.

    Used before the last-admin guard check: without this, two concurrent requests demoting or
    deactivating two *different* admins could each read "1 other active admin" and both pass,
    leaving zero. Postgres doesn't allow `FOR UPDATE` with an aggregate, so this locks the actual
    rows and the caller counts them in Python instead of using count_active_admins() here.
    """
    stmt = select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)).with_for_update()
    return list(db.scalars(stmt).all())


def list_users(
    db: Session, *, role: UserRole | None = None, is_active: bool | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[User], int]:
    stmt = select(User).order_by(User.id)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    return paginate(db, stmt, limit=limit, offset=offset)
