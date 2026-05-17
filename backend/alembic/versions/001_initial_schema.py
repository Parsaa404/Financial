"""Initial schema — all tables, indexes, and constraints.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-05-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default="false"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("profile", JSONB, nullable=False, server_default="{}"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_premium", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── refresh_tokens ──
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("device_info", JSONB, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])

    # ── audit_logs ──
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("old_data", JSONB, nullable=True),
        sa.Column("new_data", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── accounts ──
    op.create_table(
        "accounts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("balance_cents", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("credit_limit_cents", sa.BigInteger(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type IN ('checking','savings','credit','cash','investment')", name="ck_accounts_type"),
    )

    # ── transactions ──
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("subcategory", sa.String(50), nullable=True),
        sa.Column("category_source", sa.String(10), server_default="ai"),
        sa.Column("necessity_score", sa.SmallInteger(), nullable=True),
        sa.Column("merchant", sa.String(200), nullable=True),
        sa.Column("merchant_clean", sa.String(200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tags", ARRAY(sa.String()), nullable=True),
        sa.Column("transacted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("is_recurring", sa.Boolean(), server_default="false"),
        sa.Column("recurring_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(20), server_default="manual"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type IN ('income','expense','transfer')", name="ck_txn_type"),
        sa.CheckConstraint("category_source IN ('ai','user','rule')", name="ck_txn_cat_src"),
        sa.CheckConstraint("source IN ('manual','csv','bank_sync')", name="ck_txn_source"),
        sa.CheckConstraint("necessity_score BETWEEN 0 AND 10", name="ck_txn_necessity"),
        sa.UniqueConstraint("account_id", "external_id", name="uq_txn_acct_ext"),
    )
    op.create_index("idx_txn_user_date", "transactions", ["user_id", sa.text("transacted_at DESC")], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_txn_user_cat", "transactions", ["user_id", "category", sa.text("transacted_at DESC")], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_txn_merchant", "transactions", ["user_id", "merchant_clean"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_txn_recurring", "transactions", ["user_id", "merchant_clean", "amount_cents"], postgresql_where=sa.text("is_recurring = true"))
    op.create_index("idx_txn_ext_dedup", "transactions", ["account_id", "external_id"], unique=True, postgresql_where=sa.text("external_id IS NOT NULL AND deleted_at IS NULL"))

    # ── recurring_payments ──
    op.create_table(
        "recurring_payments",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("merchant", sa.String(200), nullable=True),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("next_date", sa.Date(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("is_confirmed", sa.Boolean(), server_default="false"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("frequency IN ('weekly','biweekly','monthly','yearly')", name="ck_recur_freq"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_recur_conf"),
    )

    # ── goals ──
    op.create_table(
        "goals",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("emoji", sa.String(10), nullable=True),
        sa.Column("target_amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("saved_amount_cents", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("weekly_target_cents", sa.BigInteger(), nullable=True),
        sa.Column("ai_forecast", JSONB, nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("priority", sa.SmallInteger(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active','completed','paused','failed')", name="ck_goals_status"),
    )
    op.create_index("idx_goals_active", "goals", ["user_id", "priority"], postgresql_where=sa.text("status = 'active'"))

    # ── insights ──
    op.create_table(
        "insights",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", JSONB, nullable=True),
        sa.Column("priority", sa.SmallInteger(), server_default="5"),
        sa.Column("is_read", sa.Boolean(), server_default="false"),
        sa.Column("is_actioned", sa.Boolean(), server_default="false"),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("priority BETWEEN 1 AND 10", name="ck_insights_prio"),
    )
    op.create_index("idx_insights_unread", "insights", ["user_id", "priority", sa.text("generated_at DESC")], postgresql_where=sa.text("is_read = false"))

    # ── categorization_feedback ──
    op.create_table(
        "categorization_feedback",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ai_category", sa.String(50), nullable=True),
        sa.Column("user_category", sa.String(50), nullable=False),
        sa.Column("merchant", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── daily_snapshots ──
    op.create_table(
        "daily_snapshots",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("total_balance_cents", sa.BigInteger(), nullable=True),
        sa.Column("total_spent_cents", sa.BigInteger(), nullable=True),
        sa.Column("total_income_cents", sa.BigInteger(), nullable=True),
        sa.Column("spending_by_category", JSONB, nullable=True),
        sa.UniqueConstraint("user_id", "snapshot_date", name="uq_snap_user_date"),
    )
    op.create_index("idx_snap_user_date", "daily_snapshots", ["user_id", sa.text("snapshot_date DESC")])


def downgrade() -> None:
    op.drop_table("daily_snapshots")
    op.drop_table("categorization_feedback")
    op.drop_table("insights")
    op.drop_table("goals")
    op.drop_table("recurring_payments")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
