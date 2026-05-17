"""Celery insight worker — recurring detection, daily snapshots, weekly analysis."""
import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.insight_worker.detect_recurring_payments_task")
def detect_recurring_payments_task() -> dict:
    """Detect recurring payments for all active users."""
    return asyncio.run(_detect_recurring_async())


async def _detect_recurring_async() -> dict:
    """Run recurring detection for all users."""
    from sqlalchemy import select
    from app.dependencies import async_session_factory
    from app.models.user import User
    from app.services.recurring_detector import RecurringDetectorService

    total_detected = 0
    users_processed = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(User.id).where(User.is_active == True, User.deleted_at.is_(None))
        )
        user_ids = [row[0] for row in result.all()]

    for uid in user_ids:
        try:
            async with async_session_factory() as db:
                detector = RecurringDetectorService(db)
                detected = await detector.detect_recurring(uid)
                if detected:
                    saved = await detector.save_detected(uid, detected)
                    total_detected += saved
                users_processed += 1
        except Exception as e:
            logger.error("Recurring detection failed for user %s: %s", uid, e)

    return {"users_processed": users_processed, "total_detected": total_detected}


@celery_app.task(name="app.workers.insight_worker.generate_daily_snapshots_task")
def generate_daily_snapshots_task() -> dict:
    """Generate daily financial snapshots for all active users."""
    return asyncio.run(_generate_snapshots_async())


async def _generate_snapshots_async() -> dict:
    """Create daily snapshot records for forecasting."""
    from datetime import datetime, timezone
    from sqlalchemy import select, func
    from app.dependencies import async_session_factory
    from app.models.user import User
    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.models.insight import DailySnapshot

    today = datetime.now(timezone.utc).date()
    snapshots_created = 0

    async with async_session_factory() as db:
        result = await db.execute(
            select(User.id).where(User.is_active == True, User.deleted_at.is_(None))
        )
        user_ids = [row[0] for row in result.all()]

    for uid in user_ids:
        try:
            async with async_session_factory() as db:
                # Check if snapshot already exists
                existing = await db.execute(
                    select(DailySnapshot.id).where(
                        DailySnapshot.user_id == uid,
                        DailySnapshot.snapshot_date == today,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Calculate totals
                balance_result = await db.execute(
                    select(func.coalesce(func.sum(Account.balance_cents), 0)).where(
                        Account.user_id == uid, Account.is_active == True, Account.deleted_at.is_(None)
                    )
                )
                total_balance = balance_result.scalar_one()

                snapshot = DailySnapshot(
                    user_id=uid,
                    snapshot_date=today,
                    total_balance_cents=total_balance,
                    total_spent_cents=0,
                    total_income_cents=0,
                    spending_by_category={},
                )
                db.add(snapshot)
                await db.commit()
                snapshots_created += 1
        except Exception as e:
            logger.error("Snapshot failed for user %s: %s", uid, e)

    return {"snapshots_created": snapshots_created}
