"""Auth service — password hashing, JWT creation, brute force protection."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from redis.asyncio import Redis

from app.config import get_settings
from app.dependencies import ALGORITHM

settings = get_settings()

# ── Brute force lockout rules ──
LOCKOUT_RULES: list[tuple[int, timedelta]] = [
    (3, timedelta(minutes=5)),
    (5, timedelta(minutes=30)),
    (10, timedelta(hours=24)),
]


class AuthService:
    """Authentication business logic — no direct DB queries."""

    # ── Password hashing (bcrypt cost=12) ──

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt at cost=12."""
        salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )

    # ── JWT creation ──

    @staticmethod
    def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
        """Create a signed JWT access token. Returns (token, expires_in_seconds)."""
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "jti": secrets.token_hex(16),
            "iat": now,
            "exp": now + expires_delta,
        }
        token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
        return token, int(expires_delta.total_seconds())

    @staticmethod
    def create_refresh_token() -> tuple[str, str, datetime]:
        """Create a refresh token. Returns (raw_token, sha256_hash, expires_at)."""
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        return raw_token, token_hash, expires_at

    @staticmethod
    def hash_refresh_token(raw_token: str) -> str:
        """SHA-256 hash a raw refresh token for DB lookup."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    # ── Brute force protection (Redis-backed) ──

    @staticmethod
    async def check_brute_force(
        redis: Redis, user_id: str | None, ip: str
    ) -> tuple[bool, int]:
        """Check if login is blocked due to brute force attempts.

        Returns (is_locked, lockout_seconds).
        """
        keys_to_check = [f"login_fails_ip:{ip}"]
        if user_id:
            keys_to_check.append(f"login_fails:{user_id}")

        for key in keys_to_check:
            fails_str = await redis.get(key)
            if fails_str is None:
                continue
            fails = int(fails_str)
            for threshold, lockout_duration in reversed(LOCKOUT_RULES):
                if fails >= threshold:
                    ttl = await redis.ttl(key)
                    if ttl > 0:
                        return True, ttl
        return False, 0

    @staticmethod
    async def record_failed_login(
        redis: Redis, user_id: str | None, ip: str
    ) -> None:
        """Increment failed login counters in Redis."""
        pipe = redis.pipeline()

        ip_key = f"login_fails_ip:{ip}"
        pipe.incr(ip_key)
        pipe.expire(ip_key, 86400)  # 24h max

        if user_id:
            user_key = f"login_fails:{user_id}"
            pipe.incr(user_key)
            pipe.expire(user_key, 86400)

        await pipe.execute()

    @staticmethod
    async def clear_failed_logins(
        redis: Redis, user_id: str, ip: str
    ) -> None:
        """Clear failed login counters on successful login."""
        pipe = redis.pipeline()
        pipe.delete(f"login_fails:{user_id}")
        pipe.delete(f"login_fails_ip:{ip}")
        await pipe.execute()
