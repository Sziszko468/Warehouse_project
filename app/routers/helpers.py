from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


def get_or_404[T](
    getter: Callable[[Session, int], T | None], db: Session, obj_id: int, not_found_message: str
) -> T:
    """Look up a row by id via `getter` (e.g. crud_category.get), or raise a 404.

    Collapses the `obj = crud_x.get(db, id); if obj is None: raise HTTPException(404, ...)` shape
    that was repeated across every get/update/delete endpoint in categories/suppliers/warehouses/
    products into one call.
    """
    obj = getter(db, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_message)
    return obj
