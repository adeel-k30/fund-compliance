import base64
import json
import os
import uuid
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.db.session import Base
from app.db.models import Upload, UploadStatus
from app.main import app
from app.db.deps import get_db


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://funduser:devpassword@localhost:5433/fundcompliance_test"
)

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    # Created once for the entire test session. Session-scoped means all tests share the same engine.
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(test_engine):
    """
        Creates all tables before tests, drops them after. Uses Base.metadata
        run_sync is needed because create_all is a synchronous function being called inside an async context
        begin() wraps everything in a transaction that commits automatically when the async with block exits successfully
    """

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield # all tests run here

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture()
async def db_session(test_engine):
    """
        Function-scoped (default) — a fresh transaction for every test.
        Transaction is rolled back after each test, never committed.
        Every test starts with a clean database automatically.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """
    Creates a test HTTP client pointing at the FastAPI app.
    Overrides get_db so the app uses the test session instead
    of creating a real database connection.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.clear()  # clean up overrides after test


@pytest_asyncio.fixture
async def registered_user(client):
    """
    Registers a user via the API and returns their credentials.
    Any test that needs a user just requests this fixture.
    """
    user_data = {
        "organisation_name": "Test Organisation",
        "email": "test@testorg.com",
        "password": "testpassword123"
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    return user_data  # return credentials so tests can log in


@pytest_asyncio.fixture
async def auth_headers(client, registered_user):
    """
    Logs in and returns the Authorization header.
    Any test that needs authentication just requests this fixture
    instead of manually logging in every time.
    """
    response = await client.post("/auth/token", data={
        "username": registered_user["email"],
        "password": registered_user["password"]
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_client_id(client, registered_user) -> str:
    """
    Logs in and decodes the JWT to extract the client_id claim.
    Needed when tests have to seed DB rows directly against the right tenant.
    """
    response = await client.post("/auth/token", data={
        "username": registered_user["email"],
        "password": registered_user["password"]
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload_b64 = token.split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)  # restore base64 padding
    claims = json.loads(base64.urlsafe_b64decode(payload_b64))
    return claims["client_id"]


@pytest_asyncio.fixture
async def seeded_upload(db_session, auth_client_id) -> Upload:
    """
    Inserts a minimal Upload row for the current user's client.
    Uses flush() so the row is visible within the test's transaction
    but is rolled back automatically when the test ends.
    """
    upload = Upload(
        id=str(uuid.uuid4()),
        client_id=auth_client_id,
        filename="test_emt.xlsx",
        template_type="EMT",
        template_version="3.1",
        total_rows=10,
        rows_with_issues=2,
        status=UploadStatus.COMPLETE,
        s3_key="test/test_emt.xlsx",
    )
    db_session.add(upload)
    await db_session.flush()
    return upload

