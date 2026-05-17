"""Auth API endpoints — register, login, refresh, logout."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user_id, get_db, get_redis
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
auth_svc = AuthService()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    repo = UserRepository(db)

    # Check for existing user
    existing = await repo.get_by_email(payload.email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password (bcrypt cost=12)
    password_hash = auth_svc.hash_password(payload.password)
    user = await repo.create_user(
        email=payload.email.lower(),
        password_hash=password_hash,
    )

    # Generate tokens
    access_token, expires_in = auth_svc.create_access_token(user.id)
    raw_refresh, refresh_hash, refresh_expires = auth_svc.create_refresh_token()

    await repo.store_refresh_token(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
    )

    # Audit log
    await repo.create_audit_log(
        user_id=user.id,
        action="register",
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "success": True,
        "data": AuthResponse(
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh,
                expires_in=expires_in,
            ),
            user=UserResponse.model_validate(user),
        ).model_dump(),
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }


@router.post("/login", response_model=dict)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    redis = await get_redis()
    repo = UserRepository(db)
    client_ip = _get_client_ip(request)

    # Check brute force lockout
    user = await repo.get_by_email(payload.email.lower())
    user_id_str = str(user.id) if user else None

    is_locked, lockout_seconds = await auth_svc.check_brute_force(
        redis, user_id_str, client_ip
    )
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {lockout_seconds} seconds.",
        )

    # Validate credentials
    if not user or not user.is_active:
        await auth_svc.record_failed_login(redis, user_id_str, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not auth_svc.verify_password(payload.password, user.password_hash):
        await auth_svc.record_failed_login(redis, str(user.id), client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Success — clear failed login counters
    await auth_svc.clear_failed_logins(redis, str(user.id), client_ip)
    await repo.update_last_login(user.id)

    # Generate tokens
    access_token, expires_in = auth_svc.create_access_token(user.id)
    raw_refresh, refresh_hash, refresh_expires = auth_svc.create_refresh_token()

    await repo.store_refresh_token(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
    )

    # Audit log
    await repo.create_audit_log(
        user_id=user.id,
        action="login",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
    )

    return {
        "success": True,
        "data": AuthResponse(
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh,
                expires_in=expires_in,
            ),
            user=UserResponse.model_validate(user),
        ).model_dump(),
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token — old token is revoked, new pair issued.

    If a revoked token is reused, ALL user tokens are revoked (theft detection).
    """
    repo = UserRepository(db)
    token_hash = auth_svc.hash_refresh_token(payload.refresh_token)

    # Look up token
    stored_token = await repo.get_refresh_token_by_hash(token_hash)

    if stored_token is None:
        # Possible reuse of revoked token — check if hash exists as revoked
        # If so, revoke ALL tokens for that user (security measure)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check expiration
    if stored_token.expires_at < datetime.now(timezone.utc):
        await repo.revoke_refresh_token(stored_token.id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    # Revoke the used token (rotation)
    await repo.revoke_refresh_token(stored_token.id)

    # Issue new token pair
    access_token, expires_in = auth_svc.create_access_token(stored_token.user_id)
    raw_refresh, refresh_hash, refresh_expires = auth_svc.create_refresh_token()

    await repo.store_refresh_token(
        user_id=stored_token.user_id,
        token_hash=refresh_hash,
        expires_at=refresh_expires,
    )

    return {
        "success": True,
        "data": TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
        ).model_dump(),
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "1.0"},
    }


@router.post("/logout", response_model=dict)
async def logout(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the provided refresh token."""
    repo = UserRepository(db)
    token_hash = auth_svc.hash_refresh_token(payload.refresh_token)
    stored = await repo.get_refresh_token_by_hash(token_hash)
    if stored:
        await repo.revoke_refresh_token(stored.id)

    return {
        "success": True,
        "data": MessageResponse(message="Logged out successfully").model_dump(),
    }


@router.post("/logout-all-devices", response_model=dict)
async def logout_all_devices(
    current_user_id=Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Revoke ALL refresh tokens for the current user."""
    repo = UserRepository(db)
    count = await repo.revoke_all_user_tokens(current_user_id)

    return {
        "success": True,
        "data": MessageResponse(
            message=f"Revoked {count} active sessions"
        ).model_dump(),
    }
