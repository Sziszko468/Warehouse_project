import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import get_db
from app.main import app
from app.models import Base
from app.models.user import User, UserRole
from app.security import create_access_token, hash_password

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
        hashed_password=hash_password("staffpass123"),
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
