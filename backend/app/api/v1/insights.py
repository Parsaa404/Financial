"""Insights, Onboarding, and Dashboard API endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.models.insight import Insight
from app.models.user import User
from app.repositories.account_repo import AccountRepository
from app.repositories.user_repo import UserRepository

router = APIRouter(tags=["insights"])

# ── Onboarding ──

ONBOARDING_QUESTIONS = [
    {
        "id": "goal",
        "question": "What's your main financial goal right now?",
        "options": ["save_more", "get_out_of_debt", "understand_spending", "plan_purchase"],
    },
    {
        "id": "spending_style",
        "question": "How would you describe your spending style?",
        "options": ["impulsive", "mostly_careful", "budget_conscious", "inconsistent"],
    },
    {
        "id": "pay_frequency",
        "question": "How often do you get paid?",
        "options": ["weekly", "biweekly", "monthly", "irregular"],
    },
    {
        "id": "priority",
        "question": "What matters most to you in this app?",
        "options": ["quick_decisions", "deep_insights", "goal_tracking", "spending_overview"],
    },
    {
        "id": "currency",
        "question": "Primary currency?",
        "options": ["USD", "EUR", "GBP", "OTHER"],
    },
]


class OnboardingRequest(BaseModel):
    answers: dict[str, str]


def get_dashboard_layout(profile: dict) -> dict:
    """Personalize dashboard based on onboarding answers."""
    layout = {
        "primary_widget": "spending_overview",
        "show_decision_button": "normal",
        "ai_tone": "neutral",
        "forecast_model": "regular",
        "show_alerts": True,
    }
    if profile.get("spending_style") == "impulsive":
        layout["show_decision_button"] = "prominent"
        layout["ai_tone"] = "gentle_firm"
    if profile.get("goal") == "save_more":
        layout["primary_widget"] = "savings_tracker"
        layout["ai_tone"] = "encouraging"
    if profile.get("pay_frequency") == "irregular":
        layout["forecast_model"] = "irregular_income"
    if profile.get("priority") == "quick_decisions":
        layout["primary_widget"] = "decision_engine"
    if profile.get("priority") == "goal_tracking":
        layout["primary_widget"] = "goals_tracker"
    if profile.get("priority") == "deep_insights":
        layout["primary_widget"] = "insights_feed"
    return layout


@router.get("/onboarding/questions", response_model=dict)
async def get_onboarding_questions():
    """Return the 5 onboarding questions."""
    return {"success": True, "data": ONBOARDING_QUESTIONS}


@router.post("/onboarding/complete", response_model=dict)
async def complete_onboarding(
    payload: OnboardingRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Store onboarding answers and update user profile."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = {**user.profile, **payload.answers, "onboarding_completed": True}
    await repo.update_profile(user_id, profile)

    # Update currency if specified
    currency = payload.answers.get("currency")
    if currency and currency != "OTHER":
        await repo.update_currency(user_id, currency)

    layout = get_dashboard_layout(profile)
    return {"success": True, "data": {"profile": profile, "layout": layout}}


# ── Dashboard ──

@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized dashboard data."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    acct_repo = AccountRepository(db)
    total_balance = await acct_repo.get_total_balance(user_id)
    accounts = await acct_repo.get_accounts(user_id)

    # Unread insights count
    insights_result = await db.execute(
        select(Insight).where(
            Insight.user_id == user_id, Insight.is_read == False
        ).limit(5)
    )
    unread_insights = insights_result.scalars().all()

    return {
        "success": True,
        "data": {
            "total_balance": total_balance / 100.0,
            "currency": user.currency,
            "accounts": [
                {"id": a.id, "name": a.name, "type": a.type, "balance": a.balance_cents / 100.0}
                for a in accounts
            ],
            "unread_insights_count": len(unread_insights),
            "recent_insights": [
                {"id": i.id, "title": i.title, "type": i.type, "priority": i.priority}
                for i in unread_insights
            ],
        },
    }


@router.get("/dashboard/layout", response_model=dict)
async def get_dashboard_layout_endpoint(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized dashboard layout config."""
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    layout = get_dashboard_layout(user.profile)
    return {"success": True, "data": layout}


# ── Insights ──

@router.get("/insights", response_model=dict)
async def list_insights(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all insights for the current user."""
    result = await db.execute(
        select(Insight)
        .where(Insight.user_id == user_id)
        .order_by(Insight.is_read, Insight.priority.desc(), Insight.generated_at.desc())
        .limit(50)
    )
    insights = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": i.id, "type": i.type, "title": i.title, "body": i.body,
                "data": i.data, "priority": i.priority, "is_read": i.is_read,
                "generated_at": i.generated_at.isoformat(),
            }
            for i in insights
        ],
    }


@router.patch("/insights/{insight_id}/read", response_model=dict)
async def mark_insight_read(
    insight_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark an insight as read."""
    result = await db.execute(
        update(Insight)
        .where(Insight.id == insight_id, Insight.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"success": True, "data": {"message": "Insight marked as read"}}
