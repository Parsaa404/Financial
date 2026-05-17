"""Decision API — 'Can I afford this?' endpoint."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.repositories.account_repo import AccountRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.decision import CanAffordRequest
from app.services.decision_engine import DecisionEngine

router = APIRouter(prefix="/decision", tags=["decision"])


@router.post("/can-afford", response_model=dict)
async def can_afford(
    payload: CanAffordRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Run the 'Can I afford this?' decision engine. Target: < 500ms."""
    account_repo = AccountRepository(db)
    txn_repo = TransactionRepository(db)
    engine = DecisionEngine(account_repo, txn_repo)

    result = await engine.can_afford(user_id, payload.amount)

    return {
        "success": True,
        "data": result.model_dump(),
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }


@router.get("/history", response_model=dict)
async def decision_history(
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get past decision history (placeholder — stored in future iterations)."""
    return {
        "success": True,
        "data": [],
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }
