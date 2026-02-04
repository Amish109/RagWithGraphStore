"""Test fixtures for multi-user and multi-tenant testing.

Provides pytest fixtures for:
- Async test client
- User A and User B credentials and tokens
- Admin user credentials and tokens
- Authorization headers for each user type

These fixtures enable testing of multi-tenant isolation, ensuring
users cannot access other users' data.
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.db.neo4j_client import neo4j_driver
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests.

    Uses session scope so all tests share the same event loop.
    This is required for pytest-asyncio to work correctly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client.

    Uses ASGITransport to test the FastAPI app directly without
    starting a real server. This is faster and more reliable
    for integration tests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def user_a_credentials() -> dict:
    """User A test credentials.

    Uses unique email per test run to avoid conflicts with
    previous test data.
    """
    return {
        "email": f"user_a_{uuid.uuid4().hex[:8]}@test.com",
        "password": "TestPass123!",
    }


@pytest.fixture
async def user_b_credentials() -> dict:
    """User B test credentials.

    Uses unique email per test run to avoid conflicts with
    previous test data.
    """
    return {
        "email": f"user_b_{uuid.uuid4().hex[:8]}@test.com",
        "password": "TestPass456!",
    }


@pytest.fixture
async def user_a_token(client: AsyncClient, user_a_credentials: dict) -> str:
    """Register User A and return access token.

    Creates a new user account and returns the JWT access token
    for use in authenticated requests.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json=user_a_credentials,
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
async def user_b_token(client: AsyncClient, user_b_credentials: dict) -> str:
    """Register User B and return access token.

    Creates a new user account and returns the JWT access token
    for use in authenticated requests.
    """
    response = await client.post(
        "/api/v1/auth/register",
        json=user_b_credentials,
    )
    assert response.status_code == 201, f"Registration failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
async def admin_token(client: AsyncClient) -> str:
    """Create admin user and return token.

    Steps:
    1. Register a new user
    2. Update their role to 'admin' in Neo4j
    3. Re-login to get a token with admin role
    """
    admin_creds = {
        "email": f"admin_{uuid.uuid4().hex[:8]}@test.com",
        "password": "AdminPass789!",
    }

    # Register admin
    response = await client.post(
        "/api/v1/auth/register",
        json=admin_creds,
    )
    assert response.status_code == 201, f"Admin registration failed: {response.text}"

    # Update to admin role in Neo4j
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        session.run(
            """
            MATCH (u:User {email: $email})
            SET u.role = 'admin'
        """,
            email=admin_creds["email"],
        )

    # Re-login to get token with admin role
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": admin_creds["email"], "password": admin_creds["password"]},
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def auth_headers_a(user_a_token: str) -> dict:
    """Authorization headers for User A."""
    return {"Authorization": f"Bearer {user_a_token}"}


@pytest.fixture
def auth_headers_b(user_b_token: str) -> dict:
    """Authorization headers for User B."""
    return {"Authorization": f"Bearer {user_b_token}"}


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


async def cleanup_test_users():
    """Clean up test users after tests (optional helper).

    This can be called manually or in a fixture with session scope
    to clean up test data after all tests complete.
    """
    with neo4j_driver.session(database=settings.NEO4J_DATABASE) as session:
        session.run(
            """
            MATCH (u:User)
            WHERE u.email CONTAINS '@test.com'
            DETACH DELETE u
        """
        )
