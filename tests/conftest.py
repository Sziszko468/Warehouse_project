import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.celery_app import celery_app
from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base
from app.models.user import User, UserRole
from app.security import create_access_token, hash_password
from tests.constants import SAMPLE_PASSWORD, SAMPLE_UNIT_PRICE

# Run Celery tasks synchronously and in-process - no broker/worker needed in tests, and
# `.delay()` calls execute immediately (propagating exceptions), matching how TestClient already
# executes FastAPI BackgroundTasks synchronously within the request/response cycle.
celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def _fresh_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(_fresh_schema):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, monkeypatch):
    # the app's startup lifespan (first-admin bootstrap) opens its own session via
    # app.main.SessionLocal - point that at the same in-memory test engine too.
    monkeypatch.setattr("app.main.SessionLocal", TestingSessionLocal)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(client, db_session) -> User:
    # reuse the app's own startup-created bootstrap admin (see app.main.lifespan) rather than
    # creating a second one, so tests that rely on "this is the only active admin" (e.g. the
    # last-admin guard) are actually testing that, instead of always having a fallback admin.
    user = db_session.scalar(select(User).where(User.email == settings.first_admin_email))
    assert user is not None, "bootstrap admin was not created by the app lifespan"
    return user


@pytest.fixture
def staff_user(db_session) -> User:
    user = User(
        email="staff@example.com",
        hashed_password=hash_password(SAMPLE_PASSWORD),
        full_name="Test Staff",
        role=UserRole.STAFF,
    )
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user) -> dict[str, str]:
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_headers(staff_user) -> dict[str, str]:
    token = create_access_token(staff_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def scheduled_reports_session(monkeypatch):
    # send_scheduled_stock_report runs outside any request and opens its own SessionLocal() -
    # point that at the same in-memory test engine as db_session/app.main.SessionLocal, rather
    # than the real app.database engine. Patched here (not imported from a test module) so it
    # shares this exact TestingSessionLocal/engine pair rather than risking a second one - pytest
    # loads this file as a bare "conftest" module (there's no tests/__init__.py), which is a
    # different module identity than "tests.conftest", so `from tests.conftest import ...`
    # elsewhere would bind to a second, empty in-memory database.
    from app.services import scheduled_reports

    monkeypatch.setattr(scheduled_reports, "SessionLocal", TestingSessionLocal)


# ---------------------------------------------------------------------------
# Shared master-data fixtures - used across test_products.py, test_stock_operations.py,
# test_stock_queries.py, and test_flows.py, so each doesn't hand-roll its own copy.
# ---------------------------------------------------------------------------


@pytest.fixture
def category_id(client, admin_headers) -> int:
    return client.post("/categories", json={"name": "Cables"}, headers=admin_headers).json()["id"]


@pytest.fixture
def other_category_id(client, admin_headers) -> int:
    return client.post("/categories", json={"name": "Monitors"}, headers=admin_headers).json()["id"]


@pytest.fixture
def supplier_id(client, admin_headers) -> int:
    return client.post("/suppliers", json={"name": "Acme Corp"}, headers=admin_headers).json()["id"]


@pytest.fixture
def customer_id(client, admin_headers) -> int:
    return client.post("/customers", json={"name": "Contoso Ltd"}, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_a_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse A"}, headers=admin_headers).json()["id"]


@pytest.fixture
def warehouse_b_id(client, admin_headers) -> int:
    return client.post("/warehouses", json={"name": "Warehouse B"}, headers=admin_headers).json()["id"]


@pytest.fixture
def product_id(client, admin_headers, category_id) -> int:
    payload = {
        "sku": "SKU-1",
        "name": "USB Cable",
        "category_id": category_id,
        "unit_price": SAMPLE_UNIT_PRICE,
        "min_stock_threshold": 5,
    }
    return client.post("/products", json=payload, headers=admin_headers).json()["id"]
