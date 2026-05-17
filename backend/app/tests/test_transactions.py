"""Transaction endpoint tests."""
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient, auth_headers: dict, test_account):
    """Test creating a transaction with auto-categorization."""
    response = await client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={
            "account_id": str(test_account.id),
            "amount": 49.99,
            "currency": "USD",
            "type": "expense",
            "merchant": "Starbucks Downtown",
            "transacted_at": "2026-05-15T10:30:00Z",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["amount"] == 49.99
    assert data["data"]["merchant"] == "Starbucks Downtown"
    # Should be auto-categorized by rule-based categorizer
    assert data["data"]["category"] == "Food & Dining"
    assert data["data"]["category_source"] == "rule"


@pytest.mark.asyncio
async def test_list_transactions(client: AsyncClient, auth_headers: dict, test_account):
    """Test listing transactions with pagination."""
    # Create a transaction first
    await client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={
            "account_id": str(test_account.id),
            "amount": 25.00,
            "type": "expense",
            "merchant": "Test Store",
            "transacted_at": "2026-05-15T10:00:00Z",
        },
    )

    response = await client.get(
        "/api/v1/transactions",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "pagination" in data


@pytest.mark.asyncio
async def test_correct_category(client: AsyncClient, auth_headers: dict, test_account):
    """Test category correction saves feedback."""
    # Create transaction
    create_resp = await client.post(
        "/api/v1/transactions",
        headers=auth_headers,
        json={
            "account_id": str(test_account.id),
            "amount": 30.00,
            "type": "expense",
            "merchant": "Random Place",
            "transacted_at": "2026-05-15T12:00:00Z",
        },
    )
    txn_id = create_resp.json()["data"]["id"]

    # Correct the category
    response = await client.post(
        f"/api/v1/transactions/{txn_id}/correct-category",
        headers=auth_headers,
        json={"user_category": "Healthcare"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["new"] == "Healthcare"
