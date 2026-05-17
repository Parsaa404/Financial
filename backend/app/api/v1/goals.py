"""Goals API endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.models.goal import Goal

router = APIRouter(prefix="/goals", tags=["goals"])


class GoalCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    emoji: str | None = Field(None, max_length=10)
    target_amount: float = Field(..., gt=0, le=10_000_000)
    currency: str = Field(default="USD", max_length=3)
    deadline: str | None = None
    priority: int = Field(default=1, ge=1, le=10)


class GoalUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    emoji: str | None = Field(None, max_length=10)
    saved_amount: float | None = Field(None, ge=0)
    status: str | None = Field(None, pattern="^(active|completed|paused|failed)$")
    priority: int | None = Field(None, ge=1, le=10)


def _goal_response(g: Goal) -> dict:
    return {
        "id": g.id, "title": g.title, "emoji": g.emoji,
        "target_amount": g.target_amount_cents / 100.0,
        "saved_amount": g.saved_amount_cents / 100.0,
        "currency": g.currency,
        "progress_pct": round((g.saved_amount_cents / max(g.target_amount_cents, 1)) * 100, 1),
        "deadline": g.deadline.isoformat() if g.deadline else None,
        "status": g.status, "priority": g.priority,
        "ai_forecast": g.ai_forecast,
        "created_at": g.created_at.isoformat(),
    }


@router.get("", response_model=dict)
async def list_goals(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(Goal.user_id == user_id, Goal.deleted_at.is_(None))
        .order_by(Goal.priority, Goal.created_at)
    )
    goals = result.scalars().all()
    return {"success": True, "data": [_goal_response(g) for g in goals]}


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    from dateutil import parser as dateparser
    deadline = dateparser.parse(payload.deadline).date() if payload.deadline else None

    goal = Goal(
        user_id=user_id, title=payload.title, emoji=payload.emoji,
        target_amount_cents=int(payload.target_amount * 100),
        currency=payload.currency, deadline=deadline, priority=payload.priority,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return {"success": True, "data": _goal_response(goal)}


@router.get("/{goal_id}", response_model=dict)
async def get_goal(
    goal_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True, "data": _goal_response(goal)}


@router.patch("/{goal_id}", response_model=dict)
async def update_goal(
    goal_id: uuid.UUID, payload: GoalUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if "saved_amount" in updates:
        updates["saved_amount_cents"] = int(updates.pop("saved_amount") * 100)
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        await db.execute(
            update(Goal).where(Goal.id == goal_id, Goal.user_id == user_id).values(**updates)
        )
        await db.commit()
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True, "data": _goal_response(goal)}


@router.delete("/{goal_id}", response_model=dict)
async def delete_goal(
    goal_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        update(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        .values(deleted_at=datetime.now(timezone.utc))
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True, "data": {"message": "Goal deleted"}}


@router.get("/{goal_id}/forecast", response_model=dict)
async def goal_forecast(
    goal_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id, Goal.deleted_at.is_(None))
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    remaining = goal.target_amount_cents - goal.saved_amount_cents
    progress = (goal.saved_amount_cents / max(goal.target_amount_cents, 1)) * 100

    forecast = {
        "remaining_amount": remaining / 100.0,
        "progress_pct": round(progress, 1),
        "on_track": progress >= 50 if goal.deadline else True,
        "ai_forecast": goal.ai_forecast,
    }
    return {"success": True, "data": forecast}
