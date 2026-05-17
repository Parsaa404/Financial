"""Decision Engine — 'Can I afford this?' core logic."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings
from app.repositories.account_repo import AccountRepository
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.decision import CanAffordResponse, GoalImpact

logger = logging.getLogger(__name__)


def _days_until_month_end() -> int:
    """Calculate days remaining in current month."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    return (next_month - now).days


def _get_actionable_suggestion(decision: str, score: int, projected: float) -> str:
    """Generate a concrete suggestion based on the decision."""
    if decision == "SAFE":
        return "This purchase fits within your budget. Consider setting aside the equivalent amount for savings."
    elif decision == "CAUTION":
        if projected < 500:
            return "You can afford this, but it will leave your month-end balance thin. Consider waiting until after your next paycheck."
        return "This is doable but will reduce your financial cushion. Make sure no unexpected expenses are coming up."
    else:
        if projected < 0:
            return "This purchase would put you in the red before month-end. Strongly recommend postponing or finding a cheaper alternative."
        return "This purchase carries significant financial risk. Consider splitting it into smaller payments or waiting until next month."


class DecisionEngine:
    """Core 'Can I afford this?' logic — must run in < 500ms."""

    def __init__(
        self, account_repo: AccountRepository, txn_repo: TransactionRepository
    ) -> None:
        self.account_repo = account_repo
        self.txn_repo = txn_repo
        self.settings = get_settings()

    async def _get_upcoming_recurring_total(self, user_id: uuid.UUID, days: int = 30) -> int:
        """Get total upcoming recurring payments in cents."""
        from sqlalchemy import select, func
        from app.models.recurring import RecurringPayment
        from app.dependencies import async_session_factory

        async with async_session_factory() as db:
            cutoff = datetime.now(timezone.utc).date() + timedelta(days=days)
            result = await db.execute(
                select(func.coalesce(func.sum(RecurringPayment.amount_cents), 0)).where(
                    RecurringPayment.user_id == user_id,
                    RecurringPayment.is_active == True,
                    RecurringPayment.next_date <= cutoff,
                )
            )
            return result.scalar_one()

    async def _get_goals_impact(
        self, user_id: uuid.UUID, amount_cents: int
    ) -> list[GoalImpact]:
        """Assess how purchase impacts active goals."""
        from sqlalchemy import select
        from app.models.goal import Goal
        from app.dependencies import async_session_factory

        impacts = []
        async with async_session_factory() as db:
            result = await db.execute(
                select(Goal).where(
                    Goal.user_id == user_id,
                    Goal.status == "active",
                    Goal.deleted_at.is_(None),
                )
            )
            goals = result.scalars().all()

            for goal in goals:
                target = goal.target_amount_cents
                saved = goal.saved_amount_cents
                progress = (saved / max(target, 1)) * 100

                if amount_cents > saved * 0.1:
                    impacts.append(GoalImpact(
                        goal_title=goal.title,
                        current_progress_pct=round(progress, 1),
                        impact_description=f"This could slow your progress toward '{goal.title}' ({progress:.0f}% complete).",
                    ))
        return impacts

    async def _generate_explanation(
        self,
        decision: str,
        score: int,
        amount: float,
        balance: float,
        projected: float,
    ) -> str:
        """Generate AI explanation via Gemini Flash (async, non-blocking)."""
        if not self.settings.gemini_api_key:
            return self._fallback_explanation(decision, score, amount, balance)

        prompt = (
            f"In 2 concise sentences, explain this financial decision to a user. "
            f"Decision: {decision} (risk score {score}/100). "
            f"They want to spend ${amount:.2f}. Current balance: ${balance:.2f}. "
            f"Projected month-end balance after purchase: ${projected:.2f}. "
            f"Be helpful, direct, and empathetic. No jargon."
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.settings.gemini_api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.error("Gemini explanation failed: %s", e)
            return self._fallback_explanation(decision, score, amount, balance)

    @staticmethod
    def _fallback_explanation(decision: str, score: int, amount: float, balance: float) -> str:
        """Fallback explanation when AI is unavailable."""
        ratio = amount / max(balance, 0.01) * 100
        if decision == "SAFE":
            return f"This ${amount:.2f} purchase represents {ratio:.0f}% of your balance and fits comfortably within your budget."
        elif decision == "CAUTION":
            return f"Spending ${amount:.2f} ({ratio:.0f}% of balance) is possible but will tighten your finances this month."
        return f"At ${amount:.2f} ({ratio:.0f}% of balance), this purchase poses a significant risk to your financial stability."

    async def can_afford(self, user_id: uuid.UUID, amount: float) -> CanAffordResponse:
        """Core decision logic — parallel data fetch, risk scoring, AI explanation."""
        amount_cents = int(amount * 100)

        # Parallel data fetching
        balance_cents, (avg_daily, volatility), upcoming_cents, goals_impact = await asyncio.gather(
            self.account_repo.get_total_balance(user_id),
            self.txn_repo.get_spending_velocity(user_id, days=14),
            self._get_upcoming_recurring_total(user_id, days=30),
            self._get_goals_impact(user_id, amount_cents),
        )

        available_cents = balance_cents - upcoming_cents
        days_left = _days_until_month_end()
        projected_cents = available_cents - int(avg_daily * days_left) - amount_cents

        # Risk scoring (0-100)
        score = 0
        purchase_ratio = amount_cents / max(balance_cents, 1)
        score += min(int(purchase_ratio * 40), 40)

        projected_usd = projected_cents / 100.0
        if projected_usd < 0:
            score += 30
        elif projected_usd < 200:
            score += 20
        elif projected_usd < 500:
            score += 10

        if volatility > 0.3:
            score += 15

        upcoming_ratio = upcoming_cents / max(balance_cents, 1)
        score += min(int(upcoming_ratio * 15), 15)
        score = min(score, 100)

        decision = "SAFE" if score < 30 else "CAUTION" if score < 60 else "RISKY"

        # AI explanation (async, non-blocking)
        balance_usd = balance_cents / 100.0
        explanation = await self._generate_explanation(
            decision, score, amount, balance_usd, projected_usd
        )

        suggestion = _get_actionable_suggestion(decision, score, projected_usd)

        return CanAffordResponse(
            decision=decision,
            risk_score=score,
            available_now=available_cents / 100.0,
            available_after=(available_cents - amount_cents) / 100.0,
            month_end_projected=projected_usd,
            days_until_payday=None,
            goals_impact=goals_impact,
            explanation=explanation,
            suggestion=suggestion,
            upcoming_bills_30d=upcoming_cents / 100.0,
        )
