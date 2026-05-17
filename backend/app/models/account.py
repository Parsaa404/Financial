"""Account ORM model."""
import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Account(TimestampMixin, Base):
    """Financial account — checking, savings, credit, cash, or investment."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "type IN ('checking', 'savings', 'credit', 'cash', 'investment')",
            name="ck_accounts_type",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Money stored as BIGINT cents — $19.99 = 1999
    balance_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    credit_limit_cents: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", lazy="noload")
