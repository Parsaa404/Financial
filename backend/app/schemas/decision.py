"""Decision engine schemas."""
from pydantic import BaseModel, Field


class CanAffordRequest(BaseModel):
    """Input for the 'Can I afford this?' decision."""
    amount: float = Field(..., gt=0, le=1_000_000, description="Amount in currency units")
    description: str | None = Field(None, max_length=200)


class GoalImpact(BaseModel):
    """Impact of a purchase on a specific goal."""
    goal_title: str
    current_progress_pct: float
    impact_description: str


class CanAffordResponse(BaseModel):
    """Decision engine result."""
    decision: str  # SAFE, CAUTION, RISKY
    risk_score: int  # 0-100
    available_now: float
    available_after: float
    month_end_projected: float
    days_until_payday: int | None
    goals_impact: list[GoalImpact]
    explanation: str
    suggestion: str
    upcoming_bills_30d: float
