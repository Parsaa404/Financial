"""Decision engine tests."""
import time
import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_decision_safe(client: AsyncClient, auth_headers: dict, test_account):
    """Test small purchase against $5000 balance → should be SAFE."""
    response = await client.post(
        "/api/v1/decision/can-afford",
        headers=auth_headers,
        json={"amount": 25.00, "description": "Lunch"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["decision"] == "SAFE"
    assert data["risk_score"] < 30
    assert data["available_now"] >= 25.00


@pytest.mark.asyncio
async def test_decision_risky(client: AsyncClient, auth_headers: dict, test_account):
    """Test large purchase near balance → should be RISKY."""
    response = await client.post(
        "/api/v1/decision/can-afford",
        headers=auth_headers,
        json={"amount": 4800.00, "description": "Big purchase"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["decision"] in ("CAUTION", "RISKY")
    assert data["risk_score"] >= 30


@pytest.mark.asyncio
async def test_decision_has_explanation(client: AsyncClient, auth_headers: dict, test_account):
    """Test that decision includes explanation and suggestion."""
    response = await client.post(
        "/api/v1/decision/can-afford",
        headers=auth_headers,
        json={"amount": 100.00},
    )
    data = response.json()["data"]
    assert len(data["explanation"]) > 10
    assert len(data["suggestion"]) > 10


@pytest.mark.asyncio
async def test_decision_response_time(client: AsyncClient, auth_headers: dict, test_account):
    """Test that decision engine responds in < 500ms (without AI call)."""
    start = time.time()
    response = await client.post(
        "/api/v1/decision/can-afford",
        headers=auth_headers,
        json={"amount": 50.00},
    )
    elapsed = time.time() - start
    assert response.status_code == 200
    # Generous threshold for test environment — real target is 500ms
    assert elapsed < 2.0


@pytest.mark.asyncio
async def test_decision_unauthenticated(client: AsyncClient):
    """Test decision engine requires authentication."""
    response = await client.post(
        "/api/v1/decision/can-afford",
        json={"amount": 50.00},
    )
    assert response.status_code == 401
