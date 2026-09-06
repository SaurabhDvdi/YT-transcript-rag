"""Auth Pydantic schemas: requests, responses, and domain models."""

from src.schemas.base import CamelModel


class UserProfile(CamelModel):
    id: str
    email: str
    created_at: str


class AuthTokenPair(CamelModel):
    access_token: str
    refresh_token: str
    expires_in: int  # access token TTL in seconds
    token_type: str = "Bearer"


class AuthResponse(CamelModel):
    success: bool = True
    user: UserProfile
    tokens: AuthTokenPair
    request_id: str | None = None


class ProfileResponse(CamelModel):
    success: bool = True
    user: UserProfile
    request_id: str | None = None


class RegisterRequest(CamelModel):
    email: str
    password: str


class LoginRequest(CamelModel):
    email: str
    password: str


class RefreshRequest(CamelModel):
    refresh_token: str


class MigrateSessionRequest(CamelModel):
    session_id: str


class MigrateSessionResponse(CamelModel):
    success: bool = True
    migrated_count: int
    request_id: str | None = None


class DeleteAccountResponse(CamelModel):
    success: bool = True
    message: str = "Account deleted."
    request_id: str | None = None


class LogoutResponse(CamelModel):
    success: bool = True
    request_id: str | None = None
