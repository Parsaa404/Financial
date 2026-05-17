"""Transaction API endpoints — CRUD, CSV import, category correction."""
import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db
from app.repositories.transaction_repo import TransactionRepository
from app.schemas.transaction import (
    CSVImportResponse,
    CategoryCorrectionRequest,
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.categorizer import CategorizationService

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _txn_to_response(txn) -> dict:
    """Convert Transaction ORM model to response dict (cents → dollars)."""
    return {
        "id": txn.id,
        "account_id": txn.account_id,
        "amount": txn.amount_cents / 100.0,
        "currency": txn.currency,
        "type": txn.type,
        "category": txn.category,
        "subcategory": txn.subcategory,
        "category_source": txn.category_source,
        "necessity_score": txn.necessity_score,
        "merchant": txn.merchant,
        "note": txn.note,
        "tags": txn.tags,
        "transacted_at": txn.transacted_at.isoformat(),
        "is_recurring": txn.is_recurring,
        "source": txn.source,
        "created_at": txn.created_at.isoformat(),
    }


@router.get("", response_model=dict)
async def list_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    category: str | None = None,
    type: str | None = None,
    search: str | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with pagination and filters."""
    repo = TransactionRepository(db)
    items, total = await repo.get_transactions(
        user_id, page=page, per_page=per_page,
        category=category, txn_type=type, search=search,
    )
    return {
        "success": True,
        "data": [_txn_to_response(t) for t in items],
        "pagination": {
            "total": total, "page": page, "per_page": per_page,
            "has_next": page * per_page < total,
        },
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new transaction with auto-categorization."""
    repo = TransactionRepository(db)
    categorizer = CategorizationService()

    amount_cents = int(payload.amount * 100)
    merchant_clean = categorizer.clean_merchant_name(payload.merchant or "")

    # Auto-categorize if no category provided
    cat_result = None
    if not payload.category and payload.merchant:
        user_rules = await repo.get_user_merchant_rules(user_id)
        cat_result = await categorizer.categorize(
            merchant=payload.merchant,
            amount_cents=amount_cents,
            transacted_at=payload.transacted_at.isoformat(),
            user_rules=user_rules,
        )

    txn = await repo.create_transaction(
        user_id=user_id,
        account_id=payload.account_id,
        amount_cents=amount_cents,
        currency=payload.currency,
        type=payload.type,
        category=payload.category or (cat_result["category"] if cat_result else None),
        subcategory=payload.subcategory or (cat_result.get("subcategory") if cat_result else None),
        category_source="user" if payload.category else (cat_result["category_source"] if cat_result else "rule"),
        necessity_score=cat_result.get("necessity_score") if cat_result else None,
        merchant=payload.merchant,
        merchant_clean=merchant_clean,
        note=payload.note,
        tags=payload.tags,
        transacted_at=payload.transacted_at,
        source="manual",
    )

    return {"success": True, "data": _txn_to_response(txn)}


@router.get("/{txn_id}", response_model=dict)
async def get_transaction(
    txn_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction by ID."""
    repo = TransactionRepository(db)
    txn = await repo.get_by_id(txn_id, user_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True, "data": _txn_to_response(txn)}


@router.patch("/{txn_id}", response_model=dict)
async def update_transaction(
    txn_id: uuid.UUID,
    payload: TransactionUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction."""
    repo = TransactionRepository(db)
    updates = payload.model_dump(exclude_unset=True)
    if "amount" in updates:
        updates["amount_cents"] = int(updates.pop("amount") * 100)
    txn = await repo.update_transaction(txn_id, user_id, **updates)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True, "data": _txn_to_response(txn)}


@router.delete("/{txn_id}", response_model=dict)
async def delete_transaction(
    txn_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a transaction."""
    repo = TransactionRepository(db)
    deleted = await repo.soft_delete(txn_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True, "data": {"message": "Transaction deleted"}}


@router.post("/import-csv", response_model=dict)
async def import_csv(
    file: UploadFile = File(...),
    account_id: uuid.UUID = Query(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Import transactions from CSV with deduplication."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    categorizer = CategorizationService()

    transactions: list[dict] = []
    errors = 0
    total = 0

    for row in reader:
        total += 1
        try:
            amount_str = row.get("amount", row.get("Amount", "0"))
            amount = abs(float(amount_str.replace(",", "").replace("$", "")))
            amount_cents = int(amount * 100)

            date_str = row.get("date", row.get("Date", row.get("transacted_at", "")))
            from dateutil import parser as dateparser
            transacted_at = dateparser.parse(date_str)

            merchant = row.get("merchant", row.get("Merchant", row.get("description", row.get("Description", ""))))
            merchant_clean = categorizer.clean_merchant_name(merchant)

            # Generate external_id for deduplication
            dedup_str = f"{date_str}|{amount_str}|{merchant}"
            external_id = hashlib.md5(dedup_str.encode()).hexdigest()

            txn_type = "expense"
            if float(amount_str.replace(",", "").replace("$", "")) > 0 and "income" in row.get("type", "").lower():
                txn_type = "income"

            transactions.append({
                "user_id": user_id,
                "account_id": account_id,
                "amount_cents": amount_cents,
                "currency": row.get("currency", "USD"),
                "type": txn_type,
                "merchant": merchant,
                "merchant_clean": merchant_clean,
                "transacted_at": transacted_at,
                "source": "csv",
                "external_id": external_id,
            })
        except Exception:
            errors += 1

    repo = TransactionRepository(db)
    imported = await repo.bulk_create(transactions)

    return {
        "success": True,
        "data": CSVImportResponse(
            total_rows=total,
            imported=imported,
            duplicates_skipped=total - imported - errors,
            errors=errors,
        ).model_dump(),
    }


@router.post("/{txn_id}/correct-category", response_model=dict)
async def correct_category(
    txn_id: uuid.UUID,
    payload: CategoryCorrectionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Correct a transaction's category — saves feedback for AI learning."""
    repo = TransactionRepository(db)
    txn = await repo.get_by_id(txn_id, user_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    old_category = txn.category
    await repo.save_category_feedback(
        transaction_id=txn_id, user_id=user_id,
        ai_category=old_category, user_category=payload.user_category,
        merchant=txn.merchant,
    )
    await repo.update_transaction(
        txn_id, user_id, category=payload.user_category, category_source="user"
    )

    return {"success": True, "data": {"message": "Category updated", "old": old_category, "new": payload.user_category}}
