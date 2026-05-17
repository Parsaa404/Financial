"""Transaction ORM model."""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Transaction(TimestampMixin, Base):
    """Financial transaction — income, expense, or transfer.

    Amount is stored as BIGINT cents: $19.99 = 1999.
    Category is assigned by AI, user, or rule-based system.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense', 'transfer')",
            name="ck_transactions_type",
        ),
        CheckConstraint(
            "category_source IN ('ai', 'user', 'rule')",
            name="ck_transactions_category_source",
        ),
        CheckConstraint(
            "source IN ('manual', 'csv', 'bank_sync')",
            name="ck_transactions_source",
        ),
        CheckConstraint(
            "necessity_score BETWEEN 0 AND 10",
            name="ck_transactions_necessity_score",
        ),
        UniqueConstraint(
            "account_id", "external_id", name="uq_transactions_account_external"
        ),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    # Money as BIGINT cents — never float/decimal
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category_source: Mapped[str] = mapped_column(
        String(10), default="ai", server_default="ai"
    )
    necessity_score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    merchant_clean: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    transacted_at: Mapped[datetime] = mapped_column(nullable=False)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20), default="manual", server_default="manual"
    )
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class CategorizationFeedback(Base):
    """Records when a user corrects an AI category — used for learning."""

    __tablename__ = "categorization_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    ai_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_category: Mapped[str] = mapped_column(String(50), nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, server_default="now()"
    )
