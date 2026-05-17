"""Goal ORM model."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Goal(TimestampMixin, Base):
    """Financial goal — savings target with deadline and AI forecast."""

    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'paused', 'failed')",
            name="ck_goals_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Money as BIGINT cents
    target_amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    saved_amount_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekly_target_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ai_forecast: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )
    priority: Mapped[int] = mapped_column(SmallInteger, default=1)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="goals")
