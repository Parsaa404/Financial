"""Auth endpoint tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "StrongPass123!",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]["tokens"]
    assert "refresh_token" in data["data"]["tokens"]
    assert data["data"]["user"]["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user: dict):
    """Test registration with existing email returns 409."""
    response = await client.post("/api/v1/auth/register", json={
        "email": test_user["email"],
        "password": "AnotherPass123!",
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: dict):
    """Test successful login returns tokens."""
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": test_user["password"],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "access_token" in data["data"]["tokens"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: dict):
    """Test login with wrong password returns 401."""
    response = await client.post("/api/v1/auth/login", json={
        "email": test_user["email"],
        "password": "wrong-password",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration with short password fails validation."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "short",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_logout_all_devices(client: AsyncClient, auth_headers: dict):
    """Test logout-all-devices revokes sessions."""
    response = await client.post(
        "/api/v1/auth/logout-all-devices",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient):
    """Test accessing protected route without token returns 401."""
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401
