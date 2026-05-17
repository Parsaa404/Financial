"""Forecast API endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.repositories.transaction_repo import TransactionRepository
from app.services.forecaster import ForecasterService

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/monthly", response_model=dict)
async def monthly_forecast(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly income/expense forecast."""
    txn_repo = TransactionRepository(db)
    forecaster = ForecasterService(txn_repo)
    result = await forecaster.get_monthly_forecast(user_id)
    return {
        "success": True,
        "data": result.model_dump(),
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }


@router.get("/cashflow", response_model=dict)
async def cashflow_forecast(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get daily cashflow timeline for the next 30 days."""
    txn_repo = TransactionRepository(db)
    forecaster = ForecasterService(txn_repo)
    days = await forecaster.get_cashflow(user_id, days=30)
    return {
        "success": True,
        "data": [d.model_dump() for d in days],
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }
