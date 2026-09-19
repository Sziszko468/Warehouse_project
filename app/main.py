from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.crud import user as crud_user
from app.database import SessionLocal
from app.exceptions import register_exception_handlers
from app.models.user import UserRole
from app.routers import auth, categories, products, stock, suppliers, users, warehouses

tags_metadata = [
    {"name": "auth", "description": "Registration, login, and the current user."},
    {"name": "users", "description": "Admin-only user management."},
    {"name": "categories", "description": "Product categories."},
    {"name": "suppliers", "description": "Suppliers."},
    {"name": "products", "description": "Products."},
    {"name": "warehouses", "description": "Warehouses."},
    {
        "name": "stock",
        "description": "Stock levels, low-stock alerts, movement history, and stock in/out/transfer operations.",
    },
    {"name": "ops", "description": "Operational endpoints."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Registration always creates staff users, so without this nothing could ever become
    # admin. Idempotent: only fires while there are zero active admins.
    db = SessionLocal()
    try:
        if crud_user.count_active_admins(db) == 0:
            crud_user.create_user(
                db,
                email=settings.first_admin_email,
                password=settings.first_admin_password,
                full_name="Admin",
                role=UserRole.ADMIN,
            )
            db.commit()
    finally:
        db.close()
    yield


app = FastAPI(
    title="StockFlow",
    description="Warehouse Management System REST API",
    version="0.1.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(warehouses.router)
app.include_router(stock.router)


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}
