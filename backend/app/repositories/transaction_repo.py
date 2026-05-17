"""Transaction repository — all DB queries for transactions."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import CategorizationFeedback, Transaction


class TransactionRepository:
    """Database operations for Transaction and CategorizationFeedback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_transaction(self, **kwargs) -> Transaction:
        """Create a new transaction."""
        txn = Transaction(**kwargs)
        self.db.add(txn)
        await self.db.commit()
        await self.db.refresh(txn)
        return txn

    async def get_transactions(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        per_page: int = 20,
        category: str | None = None,
        txn_type: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Transaction], int]:
        """Get paginated transactions with optional filters. Returns (items, total)."""
        query = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.deleted_at.is_(None),
        )

        if category:
            query = query.where(Transaction.category == category)
        if txn_type:
            query = query.where(Transaction.type == txn_type)
        if search:
            query = query.where(
                Transaction.merchant.ilike(f"%{search}%")
                | Transaction.note.ilike(f"%{search}%")
            )

        # Count total
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Fetch page
        query = query.order_by(Transaction.transacted_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await self.db.execute(query)

        return list(result.scalars().all()), total

    async def get_by_id(self, txn_id: uuid.UUID, user_id: uuid.UUID) -> Transaction | None:
        """Get transaction by ID with ownership check."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.id == txn_id,
                Transaction.user_id == user_id,
                Transaction.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_transaction(
        self, txn_id: uuid.UUID, user_id: uuid.UUID, **kwargs
    ) -> Transaction | None:
        """Update transaction fields."""
        allowed = {
            "amount_cents", "currency", "type", "category", "subcategory",
            "category_source", "necessity_score", "merchant", "merchant_clean",
            "note", "tags", "transacted_at", "is_recurring",
        }
        filtered = {k: v for k, v in kwargs.items() if k in allowed}
        if not filtered:
            return await self.get_by_id(txn_id, user_id)

        filtered["updated_at"] = datetime.now(timezone.utc)
        await self.db.execute(
            update(Transaction)
            .where(Transaction.id == txn_id, Transaction.user_id == user_id)
            .values(**filtered)
        )
        await self.db.commit()
        return await self.get_by_id(txn_id, user_id)

    async def soft_delete(self, txn_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Soft-delete a transaction."""
        result = await self.db.execute(
            update(Transaction)
            .where(Transaction.id == txn_id, Transaction.user_id == user_id)
            .values(deleted_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def bulk_create(self, transactions: list[dict]) -> int:
        """Bulk insert transactions, skip duplicates via external_id."""
        created = 0
        for txn_data in transactions:
            # Check for duplicate via external_id
            if txn_data.get("external_id"):
                existing = await self.db.execute(
                    select(Transaction.id).where(
                        Transaction.account_id == txn_data["account_id"],
                        Transaction.external_id == txn_data["external_id"],
                        Transaction.deleted_at.is_(None),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

            txn = Transaction(**txn_data)
            self.db.add(txn)
            created += 1

        if created:
            await self.db.commit()
        return created

    async def get_spending_by_period(
        self, user_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[Transaction]:
        """Get expense transactions in a date range."""
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.transacted_at >= start,
                Transaction.transacted_at <= end,
                Transaction.deleted_at.is_(None),
            ).order_by(Transaction.transacted_at.desc())
        )
        return list(result.scalars().all())

    async def get_spending_velocity(
        self, user_id: uuid.UUID, days: int = 14
    ) -> tuple[float, float]:
        """Get average daily spending and volatility over N days.

        Returns (avg_daily_cents, volatility_ratio).
        """
        from datetime import timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Transaction.amount_cents), 0),
                func.coalesce(func.count(Transaction.id), 0),
            ).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.transacted_at >= start,
                Transaction.transacted_at <= end,
                Transaction.deleted_at.is_(None),
            )
        )
        row = result.one()
        total_cents = row[0]
        count = row[1]

        avg_daily = total_cents / max(days, 1)

        # Simple volatility: stddev / mean
        if count < 2:
            return avg_daily, 0.0

        from sqlalchemy import cast, Float
        std_result = await self.db.execute(
            select(func.stddev(cast(Transaction.amount_cents, Float))).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.transacted_at >= start,
                Transaction.deleted_at.is_(None),
            )
        )
        stddev = std_result.scalar_one() or 0.0
        mean = total_cents / max(count, 1)
        volatility = stddev / max(mean, 1)

        return avg_daily, min(volatility, 2.0)

    async def save_category_feedback(
        self,
        transaction_id: uuid.UUID,
        user_id: uuid.UUID,
        ai_category: str | None,
        user_category: str,
        merchant: str | None,
    ) -> None:
        """Store user's category correction for AI learning."""
        feedback = CategorizationFeedback(
            transaction_id=transaction_id,
            user_id=user_id,
            ai_category=ai_category,
            user_category=user_category,
            merchant=merchant,
        )
        self.db.add(feedback)
        await self.db.commit()

    async def get_user_merchant_rules(self, user_id: uuid.UUID) -> dict[str, str]:
        """Get user's personal merchant→category mapping from feedback."""
        result = await self.db.execute(
            select(
                CategorizationFeedback.merchant,
                CategorizationFeedback.user_category,
            )
            .where(CategorizationFeedback.user_id == user_id)
            .where(CategorizationFeedback.merchant.isnot(None))
            .order_by(CategorizationFeedback.created_at.desc())
        )
        rules: dict[str, str] = {}
        for merchant, category in result.all():
            if merchant and merchant.lower() not in rules:
                rules[merchant.lower()] = category
        return rules
