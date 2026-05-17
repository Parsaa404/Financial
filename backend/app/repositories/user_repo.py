"""User repository — all DB queries for users and refresh tokens."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import AuditLog, RefreshToken, User


class UserRepository:
    """Database operations for User, RefreshToken, and AuditLog.

    All queries use SQLAlchemy ORM — never raw SQL strings.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── User CRUD ──

    async def create_user(self, email: str, password_hash: str) -> User:
        """Create a new user with hashed password."""
        user = User(email=email, password_hash=password_hash)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Find user by email (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower(),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Find user by ID."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update last_login_at timestamp."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def update_profile(self, user_id: uuid.UUID, profile: dict) -> User | None:
        """Update user profile JSONB."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(profile=profile, updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return await self.get_by_id(user_id)

    async def update_currency(self, user_id: uuid.UUID, currency: str) -> None:
        """Update user's preferred currency."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(currency=currency, updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    # ── Refresh Token operations ──

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        device_info: dict | None = None,
    ) -> RefreshToken:
        """Store a SHA-256 hashed refresh token."""
        rt = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            device_info=device_info,
        )
        self.db.add(rt)
        await self.db.commit()
        return rt

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Find a refresh token by its SHA-256 hash."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token_id: uuid.UUID) -> None:
        """Revoke a specific refresh token."""
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revoke ALL refresh tokens for a user (stolen token protection)."""
        result = await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount  # type: ignore[return-value]

    # ── Audit Log ──

    async def create_audit_log(
        self,
        user_id: uuid.UUID | None,
        action: str,
        resource: str | None = None,
        resource_id: uuid.UUID | None = None,
        old_data: dict | None = None,
        new_data: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Append an audit log entry — never deleted."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            old_data=old_data,
            new_data=new_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.commit()
