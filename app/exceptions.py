from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class InsufficientStockError(Exception):
    def __init__(self, message: str = "Insufficient stock for this operation"):
        self.message = message


class InvalidStockOperationError(Exception):
    def __init__(self, message: str):
        self.message = message


class NotFoundError(Exception):
    def __init__(self, message: str = "Resource not found"):
        self.message = message


class LastAdminError(Exception):
    def __init__(self, message: str = "Cannot demote or deactivate the last active admin"):
        self.message = message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(request: Request, exc: InsufficientStockError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})

    @app.exception_handler(InvalidStockOperationError)
    async def handle_invalid_stock_operation(request: Request, exc: InvalidStockOperationError) -> JSONResponse:
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
            status_code=status.HTTP_409_CONFLICT, content={"detail": "Request conflicts with existing data"}
        )
