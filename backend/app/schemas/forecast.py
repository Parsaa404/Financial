"""Forecast schemas."""
from pydantic import BaseModel


class MonthlyForecast(BaseModel):
    """Monthly income/expense forecast."""
    month: str
    projected_income: float
    projected_expenses: float
    projected_savings: float
    confidence: float  # 0-1
    breakdown: dict[str, float]  # category → amount


class CashflowDay(BaseModel):
    """Single day in cashflow timeline."""
    date: str
    projected_balance: float
    income: float
    expenses: float
    is_payday: bool = False
    recurring_bills: list[str] = []


class ForecastResponse(BaseModel):
    """Forecast API response."""
    monthly: list[MonthlyForecast]
    avg_monthly_income: float
    avg_monthly_expenses: float
    savings_rate: float
