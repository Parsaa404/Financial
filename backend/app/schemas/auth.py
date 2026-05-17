"""Auth Pydantic schemas — request/response models for authentication."""
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration payload."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Login payload."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Token refresh payload."""
    refresh_token: str


class TokenResponse(BaseModel):
    """JWT token pair returned on login/register/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Public user data — never includes password_hash."""
    id: uuid.UUID
    email: str
    email_verified: bool
    currency: str
    timezone: str
    is_active: bool
    is_premium: bool
    profile: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Combined auth response with tokens and user data."""
    tokens: TokenResponse
    user: UserResponse


class MessageResponse(BaseModel):
    """Simple message response for logout etc."""
    message: str
