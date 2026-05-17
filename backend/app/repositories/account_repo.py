"""Account repository — all DB queries for financial accounts."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class AccountRepository:
    """Database operations for Account model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_account(
        self,
        user_id: uuid.UUID,
        name: str,
        account_type: str,
        currency: str,
        balance_cents: int = 0,
        credit_limit_cents: int | None = None,
        is_primary: bool = False,
    ) -> Account:
        """Create a new financial account."""
        account = Account(
            user_id=user_id,
            name=name,
            type=account_type,
            currency=currency,
            balance_cents=balance_cents,
            credit_limit_cents=credit_limit_cents,
            is_primary=is_primary,
        )
        self.db.add(account)
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_accounts(self, user_id: uuid.UUID) -> list[Account]:
        """Get all active accounts for a user."""
        result = await self.db.execute(
            select(Account).where(
                Account.user_id == user_id,
                Account.deleted_at.is_(None),
            ).order_by(Account.is_primary.desc(), Account.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, account_id: uuid.UUID, user_id: uuid.UUID) -> Account | None:
        """Get account by ID with ownership check."""
        result = await self.db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
                Account.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_account(
        self, account_id: uuid.UUID, user_id: uuid.UUID, **kwargs
    ) -> Account | None:
        """Update account fields. Only allowed fields are updated."""
        allowed = {"name", "type", "currency", "balance_cents", "credit_limit_cents", "is_primary", "is_active"}
        filtered = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not filtered:
            return await self.get_by_id(account_id, user_id)

        filtered["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(Account)
            .where(Account.id == account_id, Account.user_id == user_id)
            .values(**filtered)
        )
        await self.db.commit()
        return await self.get_by_id(account_id, user_id)

    async def soft_delete(self, account_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Soft-delete an account."""
        result = await self.db.execute(
            update(Account)
            .where(Account.id == account_id, Account.user_id == user_id, Account.deleted_at.is_(None))
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_total_balance(self, user_id: uuid.UUID) -> int:
        """Get total balance across all active accounts in cents."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.coalesce(func.sum(Account.balance_cents), 0)).where(
                Account.user_id == user_id,
                Account.is_active == True,
                Account.deleted_at.is_(None),
            )
        )
        return result.scalar_one()
