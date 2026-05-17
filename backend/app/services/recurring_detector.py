"""Recurring payment detection service."""
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring import RecurringPayment
from app.models.transaction import Transaction


class RecurringDetectorService:
    """Detect recurring payments from transaction patterns."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_recurring(self, user_id: uuid.UUID) -> list[dict]:
        """Analyze transactions to find recurring payment patterns.

        Looks for: same merchant + similar amount + regular intervals.
        """
        # Get last 6 months of expense transactions
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        result = await self.db.execute(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.transacted_at >= cutoff,
                Transaction.deleted_at.is_(None),
                Transaction.merchant_clean.isnot(None),
            ).order_by(Transaction.merchant_clean, Transaction.transacted_at)
        )
        transactions = list(result.scalars().all())

        # Group by cleaned merchant name
        merchant_groups: dict[str, list[Transaction]] = defaultdict(list)
        for txn in transactions:
            if txn.merchant_clean:
                merchant_groups[txn.merchant_clean.lower()].append(txn)

        detected: list[dict] = []

        for merchant, txns in merchant_groups.items():
            if len(txns) < 2:
                continue

            # Check for amount consistency (within 10% tolerance)
            amounts = [t.amount_cents for t in txns]
            avg_amount = sum(amounts) / len(amounts)
            amount_variance = max(abs(a - avg_amount) / max(avg_amount, 1) for a in amounts)

            if amount_variance > 0.15:
                continue  # Amounts too varied

            # Check for interval regularity
            dates = sorted([t.transacted_at for t in txns])
            intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

            if not intervals:
                continue

            avg_interval = sum(intervals) / len(intervals)
            frequency = self._classify_frequency(avg_interval)

            if not frequency:
                continue

            # Calculate confidence based on consistency
            interval_variance = sum(abs(i - avg_interval) for i in intervals) / len(intervals) / max(avg_interval, 1)
            confidence = max(0.0, min(1.0, 1.0 - interval_variance - amount_variance))

            if confidence < 0.5:
                continue

            # Predict next date
            last_date = dates[-1]
            next_date = last_date + timedelta(days=int(avg_interval))

            detected.append({
                "name": txns[0].merchant_clean or merchant,
                "merchant": merchant,
                "amount_cents": int(avg_amount),
                "currency": txns[0].currency,
                "frequency": frequency,
                "category": txns[0].category,
                "next_date": next_date.date(),
                "last_seen_at": last_date,
                "confidence": round(confidence, 3),
            })

        return detected

    @staticmethod
    def _classify_frequency(avg_days: float) -> str | None:
        """Classify interval into a frequency category."""
        if 5 <= avg_days <= 9:
            return "weekly"
        elif 12 <= avg_days <= 17:
            return "biweekly"
        elif 25 <= avg_days <= 35:
            return "monthly"
        elif 350 <= avg_days <= 380:
            return "yearly"
        return None

    async def save_detected(self, user_id: uuid.UUID, detected: list[dict]) -> int:
        """Save detected recurring payments to the database."""
        saved = 0
        for item in detected:
            # Check if already exists
            existing = await self.db.execute(
                select(RecurringPayment).where(
                    RecurringPayment.user_id == user_id,
                    RecurringPayment.merchant == item["merchant"],
                    RecurringPayment.is_active == True,
                )
            )
            if existing.scalar_one_or_none():
                continue

            rp = RecurringPayment(
                user_id=user_id,
                name=item["name"],
                merchant=item["merchant"],
                amount_cents=item["amount_cents"],
                currency=item["currency"],
                frequency=item["frequency"],
                category=item["category"],
                next_date=item["next_date"],
                last_seen_at=item["last_seen_at"],
                confidence=Decimal(str(item["confidence"])),
            )
            self.db.add(rp)
            saved += 1

        if saved:
            await self.db.commit()
        return saved
