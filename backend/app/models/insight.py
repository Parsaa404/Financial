"""Insight ORM model and DailySnapshot."""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Insight(Base):
    """AI-generated insight — spending alerts, tips, behavioral analysis."""

    __tablename__ = "insights"
    __table_args__ = (
        CheckConstraint(
            "priority BETWEEN 1 AND 10",
            name="ck_insights_priority",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(SmallInteger, default=5)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_actioned: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="insights")


class DailySnapshot(Base):
    """Pre-computed daily financial snapshot for fast forecasting."""

    __tablename__ = "daily_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_snapshots_user_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Money as BIGINT cents
    total_balance_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_spent_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_income_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    spending_by_category: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
