"""Transaction Pydantic schemas."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    """Create a new transaction."""
    account_id: uuid.UUID
    amount: float = Field(..., gt=0, le=1_000_000, description="Amount in currency units (converted to cents internally)")
    currency: str = Field(default="USD", max_length=3)
    type: str = Field(..., pattern="^(income|expense|transfer)$")
    category: str | None = Field(None, max_length=50)
    subcategory: str | None = Field(None, max_length=50)
    merchant: str | None = Field(None, min_length=1, max_length=200)
    note: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    transacted_at: datetime


class TransactionUpdate(BaseModel):
    """Update an existing transaction."""
    amount: float | None = Field(None, gt=0, le=1_000_000)
    currency: str | None = Field(None, max_length=3)
    type: str | None = Field(None, pattern="^(income|expense|transfer)$")
    category: str | None = Field(None, max_length=50)
    subcategory: str | None = Field(None, max_length=50)
    merchant: str | None = Field(None, max_length=200)
    note: str | None = Field(None, max_length=500)
    tags: list[str] | None = None
    transacted_at: datetime | None = None


class TransactionResponse(BaseModel):
    """Transaction data returned to client."""
    id: uuid.UUID
    account_id: uuid.UUID
    amount: float  # Converted from cents for display
    currency: str
    type: str
    category: str | None
    subcategory: str | None
    category_source: str
    necessity_score: int | None
    merchant: str | None
    note: str | None
    tags: list[str] | None
    transacted_at: datetime
    is_recurring: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCorrectionRequest(BaseModel):
    """User corrects AI category."""
    user_category: str = Field(..., min_length=1, max_length=50)


class CSVImportResponse(BaseModel):
    """Result of CSV import."""
    total_rows: int
    imported: int
    duplicates_skipped: int
    errors: int
