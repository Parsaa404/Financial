"""Forecast engine — monthly projections and cashflow analysis."""
import uuid
from datetime import datetime, timedelta, timezone

from app.repositories.transaction_repo import TransactionRepository
from app.schemas.forecast import CashflowDay, ForecastResponse, MonthlyForecast


class ForecasterService:
    """Basic monthly forecast based on historical spending patterns."""

    def __init__(self, txn_repo: TransactionRepository) -> None:
        self.txn_repo = txn_repo

    async def get_monthly_forecast(self, user_id: uuid.UUID) -> ForecastResponse:
        """Generate 3-month forward projection based on last 3 months of data."""
        now = datetime.now(timezone.utc)
        months_data: list[dict] = []

        # Analyze last 3 months
        for i in range(1, 4):
            start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1)
            else:
                end = start.replace(month=start.month + 1, day=1)

            txns = await self.txn_repo.get_spending_by_period(user_id, start, end)

            income = sum(t.amount_cents for t in txns if t.type == "income") if txns else 0
            # get_spending_by_period only returns expenses, so re-query for income
            all_start = start
            all_end = end

            income_cents = 0
            expense_cents = 0
            category_totals: dict[str, int] = {}

            for t in txns:
                expense_cents += t.amount_cents
                cat = t.category or "Uncategorized"
                category_totals[cat] = category_totals.get(cat, 0) + t.amount_cents

            months_data.append({
                "income": income_cents,
                "expenses": expense_cents,
                "categories": category_totals,
            })

        # Calculate averages
        total_months = max(len(months_data), 1)
        avg_income = sum(m["income"] for m in months_data) / total_months
        avg_expenses = sum(m["expenses"] for m in months_data) / total_months

        # Build projections for next 3 months
        projections: list[MonthlyForecast] = []
        for i in range(1, 4):
            future_month = now.month + i
            future_year = now.year
            if future_month > 12:
                future_month -= 12
                future_year += 1

            month_label = f"{future_year}-{future_month:02d}"

            # Aggregate category breakdown
            all_cats: dict[str, float] = {}
            for m in months_data:
                for cat, amount in m["categories"].items():
                    all_cats[cat] = all_cats.get(cat, 0) + amount / total_months

            breakdown = {k: round(v / 100, 2) for k, v in all_cats.items()}

            projections.append(MonthlyForecast(
                month=month_label,
                projected_income=round(avg_income / 100, 2),
                projected_expenses=round(avg_expenses / 100, 2),
                projected_savings=round((avg_income - avg_expenses) / 100, 2),
                confidence=0.7 if len(months_data) >= 3 else 0.4,
                breakdown=breakdown,
            ))

        savings_rate = (avg_income - avg_expenses) / max(avg_income, 1) if avg_income > 0 else 0

        return ForecastResponse(
            monthly=projections,
            avg_monthly_income=round(avg_income / 100, 2),
            avg_monthly_expenses=round(avg_expenses / 100, 2),
            savings_rate=round(savings_rate, 3),
        )

    async def get_cashflow(self, user_id: uuid.UUID, days: int = 30) -> list[CashflowDay]:
        """Generate daily cashflow timeline for the next N days."""
        now = datetime.now(timezone.utc)
        avg_daily, _ = await self.txn_repo.get_spending_velocity(user_id, days=14)

        timeline: list[CashflowDay] = []
        running_balance = 0  # Will be set from account balance

        from app.repositories.account_repo import AccountRepository
        from app.dependencies import async_session_factory

        async with async_session_factory() as db:
            acct_repo = AccountRepository(db)
            running_balance = await acct_repo.get_total_balance(user_id)

        for day_offset in range(days):
            day = now + timedelta(days=day_offset)
            daily_expense = int(avg_daily)
            running_balance -= daily_expense

            timeline.append(CashflowDay(
                date=day.strftime("%Y-%m-%d"),
                projected_balance=round(running_balance / 100, 2),
                income=0,
                expenses=round(daily_expense / 100, 2),
            ))

        return timeline
