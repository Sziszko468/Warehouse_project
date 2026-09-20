from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.messages import Messages


class InsufficientStockError(Exception):
    def __init__(self, message: str = Messages.INSUFFICIENT_STOCK_DEFAULT):
        self.message = message


class InvalidStockOperationError(Exception):
    def __init__(self, message: str):
        self.message = message


class InvalidOrderStateError(Exception):
    """Raised when an order/shipment lifecycle action (submit, confirm, receive, ship, cancel...)
    is attempted from a status that doesn't allow it."""

    def __init__(self, message: str):
        self.message = message


class NotFoundError(Exception):
    def __init__(self, message: str = Messages.RESOURCE_NOT_FOUND):
        self.message = message


class LastAdminError(Exception):
    def __init__(self, message: str = Messages.LAST_ADMIN_GUARD):
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(request: Request, exc: InsufficientStockError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})

    @app.exception_handler(InvalidStockOperationError)
    async def handle_invalid_stock_operation(request: Request, exc: InvalidStockOperationError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message})

    @app.exception_handler(InvalidOrderStateError)
    async def handle_invalid_order_state(request: Request, exc: InvalidOrderStateError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": exc.message})

    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message})

    @app.exception_handler(LastAdminError)
    async def handle_last_admin(request: Request, exc: LastAdminError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content={"detail": Messages.CONFLICTS_WITH_EXISTING_DATA}
        )
