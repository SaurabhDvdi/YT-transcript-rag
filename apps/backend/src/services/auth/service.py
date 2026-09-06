"""AuthService: registration, login, token refresh, logout, account deletion."""

import re
from datetime import UTC, datetime
from typing import Any

from src.core.config import get_settings
from src.core.errors import AppError
from src.repositories.auth import (
    AuthRepository,
    D1AuthRepository,
    InMemoryAuthRepository,
    User,
)
from src.schemas.auth import AuthResponse, AuthTokenPair, UserProfile
from src.services.auth.crypto import (
    generate_salt,
    hash_password,
    verify_password,
)
from src.services.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expires_at,
)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_MIN_PASSWORD_LEN = 8
_MAX_PASSWORD_LEN = 128
_MAX_EMAIL_LEN = 254


_DUMMY_SALT = "00" * 16
_DUMMY_HASH = "00" * 32


def _validate_email(email: str) -> str:
    """Normalize and validate an email address."""
    email = email.lower().strip()
    if len(email) > _MAX_EMAIL_LEN or not _EMAIL_RE.match(email):
        raise AppError("INVALID_EMAIL", 422, "Please provide a valid email address.")
    return email


def _validate_password(password: str) -> None:
    """Enforce minimum password requirements."""
    if len(password) < _MIN_PASSWORD_LEN:
        raise AppError(
            "INVALID_PASSWORD",
            422,
            f"Password must be at least {_MIN_PASSWORD_LEN} characters long.",
        )
    if len(password) > _MAX_PASSWORD_LEN:
        raise AppError("INVALID_PASSWORD", 422, "Password is too long.")


def _make_token_pair(
    user: User, secret: str, ttl_seconds: int, ttl_days: int
) -> tuple[AuthTokenPair, str]:
    """Create a fresh access + refresh token pair.

    Returns (AuthTokenPair, refresh_token_hex).
    """
    access_token = create_access_token(user.id, user.email, secret, ttl_seconds)
    refresh_raw, _refresh_hash = create_refresh_token()
    pair = AuthTokenPair(
        access_token=access_token,
        refresh_token=refresh_raw,
        expires_in=ttl_seconds,
    )
    return pair, refresh_raw


def _make_auth_response(
    user: User,
    pair: AuthTokenPair,
    request_id: str | None = None,
) -> AuthResponse:
    return AuthResponse(
        success=True,
        user=UserProfile(id=user.id, email=user.email, created_at=user.created_at),
        tokens=pair,
        request_id=request_id,
    )


class AuthService:
    """Auth service with D1 repository or shared InMemoryAuthRepository."""

    _instance: "AuthService | None" = None

    def __init__(self, repo: AuthRepository | None = None) -> None:
        self._repo: AuthRepository = repo if repo is not None else InMemoryAuthRepository()

    @classmethod
    def get_instance(cls, db: Any = None) -> "AuthService":
        """Factory: use D1 repository when db is present, shared InMemory singleton otherwise."""
        if db is not None:
            return cls(repo=D1AuthRepository(db))
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: "AuthService | None") -> None:
        cls._instance = instance

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register(
        self,
        email: str,
        password: str,
        request_id: str | None = None,
    ) -> AuthResponse:
        settings = get_settings()
        email = _validate_email(email)
        _validate_password(password)

        existing = await self._repo.get_user_by_email(email)
        if existing:
            raise AppError(
                "EMAIL_ALREADY_EXISTS",
                409,
                "An account with that email address already exists.",
            )

        salt = generate_salt()
        pw_hash = hash_password(password, salt)
        user = await self._repo.create_user(email, pw_hash, salt)

        pair, refresh_raw = _make_token_pair(
            user,
            settings.auth_token_secret,
            settings.access_token_ttl_seconds,
            settings.refresh_token_ttl_days,
        )
        refresh_hash = hash_refresh_token(refresh_raw)
        expires_at = refresh_token_expires_at(settings.refresh_token_ttl_days)
        await self._repo.create_session(user.id, refresh_hash, expires_at)

        return _make_auth_response(user, pair, request_id)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(
        self,
        email: str,
        password: str,
        request_id: str | None = None,
    ) -> AuthResponse:
        settings = get_settings()
        email = _validate_email(email)

        user = await self._repo.get_user_by_email(email)
        if not user:
            # Constant-time dummy verification prevents email enumeration via timing attacks
            verify_password(password, _DUMMY_SALT, _DUMMY_HASH)
            raise AppError("INVALID_CREDENTIALS", 401, "Invalid email or password.")

        if user.deleted_at is not None:
            verify_password(password, _DUMMY_SALT, _DUMMY_HASH)
            raise AppError("ACCOUNT_DELETED", 401, "This account has been deleted.")

        if not verify_password(password, user.password_salt, user.password_hash):
            raise AppError("INVALID_CREDENTIALS", 401, "Invalid email or password.")

        pair, refresh_raw = _make_token_pair(
            user,
            settings.auth_token_secret,
            settings.access_token_ttl_seconds,
            settings.refresh_token_ttl_days,
        )
        refresh_hash = hash_refresh_token(refresh_raw)
        expires_at = refresh_token_expires_at(settings.refresh_token_ttl_days)
        await self._repo.create_session(user.id, refresh_hash, expires_at)

        return _make_auth_response(user, pair, request_id)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    async def refresh(
        self,
        raw_refresh_token: str,
        request_id: str | None = None,
    ) -> AuthResponse:
        settings = get_settings()
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await self._repo.get_session_by_token_hash(token_hash)

        if session is None:
            raise AppError("SESSION_REVOKED", 401, "Refresh token is invalid or revoked.")

        if session.revoked_at is not None:
            # Token reuse detected! Active replay attack mitigation: revoke all user sessions
            await self._repo.revoke_all_user_sessions(session.user_id)
            raise AppError("SESSION_REVOKED", 401, "Refresh token has been revoked.")

        now_iso = datetime.now(UTC).isoformat()
        if session.expires_at < now_iso:
            raise AppError(
                "SESSION_EXPIRED", 401, "Refresh token has expired. Please log in again."
            )

        user = await self._repo.get_user_by_id(session.user_id)
        if not user or user.deleted_at is not None:
            raise AppError("ACCOUNT_DELETED", 401, "This account has been deleted.")

        # Rotate: revoke old session, issue new tokens
        await self._repo.revoke_session(session.id)

        pair, refresh_raw = _make_token_pair(
            user,
            settings.auth_token_secret,
            settings.access_token_ttl_seconds,
            settings.refresh_token_ttl_days,
        )
        refresh_hash = hash_refresh_token(refresh_raw)
        expires_at = refresh_token_expires_at(settings.refresh_token_ttl_days)
        await self._repo.create_session(user.id, refresh_hash, expires_at)

        return _make_auth_response(user, pair, request_id)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        session = await self._repo.get_session_by_token_hash(token_hash)
        if session:
            await self._repo.revoke_session(session.id)

    # ------------------------------------------------------------------
    # Account deletion
    # ------------------------------------------------------------------

    async def delete_account(self, user_id: str) -> None:
        await self._repo.revoke_all_user_sessions(user_id)
        await self._repo.soft_delete_user(user_id)

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self._repo.get_user_by_id(user_id)
