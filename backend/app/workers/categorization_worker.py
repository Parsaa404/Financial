"""Celery categorization worker — batch categorize uncategorized transactions."""
import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.categorization_worker.categorize_batch")
def categorize_batch(user_id: str) -> dict:
    """Batch categorize uncategorized transactions for a user."""
    return asyncio.run(_categorize_batch_async(user_id))


async def _categorize_batch_async(user_id: str) -> dict:
    """Async implementation of batch categorization."""
    from uuid import UUID
    from sqlalchemy import select, update
    from app.dependencies import async_session_factory
    from app.models.transaction import Transaction
    from app.repositories.transaction_repo import TransactionRepository
    from app.services.categorizer import CategorizationService

    categorizer = CategorizationService()
    processed = 0
    errors = 0

    async with async_session_factory() as db:
        # Get uncategorized transactions
        result = await db.execute(
            select(Transaction).where(
                Transaction.user_id == UUID(user_id),
                Transaction.category.is_(None),
                Transaction.deleted_at.is_(None),
            ).limit(100)
        )
        transactions = list(result.scalars().all())

        # Get user's personal merchant rules
        txn_repo = TransactionRepository(db)
        user_rules = await txn_repo.get_user_merchant_rules(UUID(user_id))

        for txn in transactions:
            try:
                result = await categorizer.categorize(
                    merchant=txn.merchant or "",
                    amount_cents=txn.amount_cents,
                    transacted_at=txn.transacted_at.isoformat(),
                    user_rules=user_rules,
                )

                await db.execute(
                    update(Transaction)
                    .where(Transaction.id == txn.id)
                    .values(
                        category=result["category"],
                        subcategory=result.get("subcategory"),
                        necessity_score=result.get("necessity_score"),
                        category_source=result["category_source"],
                    )
                )
                processed += 1
            except Exception as e:
                logger.error("Failed to categorize txn %s: %s", txn.id, e)
                errors += 1

        await db.commit()

    return {"processed": processed, "errors": errors}
