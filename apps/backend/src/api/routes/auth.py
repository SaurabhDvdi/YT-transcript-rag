"""Auth API routes: register, login, refresh, logout, profile, delete, migrate-session."""

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.core.errors import AppError
from src.schemas.auth import (
    DeleteAccountResponse,
    LoginRequest,
    LogoutResponse,
    MigrateSessionRequest,
    MigrateSessionResponse,
    ProfileResponse,
    RefreshRequest,
    RegisterRequest,
)
from src.services.auth.service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _get_user_id(request: Request) -> str:
    """Return authenticated user_id or raise 401."""
    user_id: str | None = getattr(request.state, "user_id", None)
    if not user_id:
        raise AppError("UNAUTHORIZED", 401, "Authentication required.")
    return user_id


def _get_auth_service(request: Request) -> AuthService:
    db = getattr(request.state, "db", None)
    return AuthService.get_instance(db)


async def _parse_json_body(request: Request) -> dict[str, Any]:
    ct = request.headers.get("content-type", "")
    if "application/json" not in ct.lower():
        raise AppError("INVALID_REQUEST", 400, "Content-Type must be application/json.")
    try:
        body = await request.json()
    except Exception:
        raise AppError("INVALID_REQUEST", 400, "Malformed JSON request body.") from None
    if not isinstance(body, dict):
        raise AppError("INVALID_REQUEST", 400, "Request body must be a JSON object.")
    return dict(body)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


@router.post("/register", status_code=201)
async def register(request: Request) -> JSONResponse:
    """Register a new user account and return an access + refresh token pair."""
    body = await _parse_json_body(request)
    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip():
        raise AppError("INVALID_EMAIL", 422, "Email is required.")
    if not isinstance(password, str) or not password:
        raise AppError("INVALID_PASSWORD", 422, "Password is required.")

    service = _get_auth_service(request)
    req = RegisterRequest(email=email.strip(), password=password)
    result = await service.register(req.email, req.password, _get_request_id(request))
    return JSONResponse(
        status_code=201,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(request: Request) -> JSONResponse:
    """Authenticate with email + password and return tokens."""
    body = await _parse_json_body(request)
    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip():
        raise AppError("INVALID_EMAIL", 422, "Email is required.")
    if not isinstance(password, str) or not password:
        raise AppError("INVALID_PASSWORD", 422, "Password is required.")

    service = _get_auth_service(request)
    req = LoginRequest(email=email.strip(), password=password)
    result = await service.login(req.email, req.password, _get_request_id(request))
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh")
async def refresh_token(request: Request) -> JSONResponse:
    """Exchange a refresh token for a new access + refresh token pair (token rotation)."""
    body = await _parse_json_body(request)
    raw_token = body.get("refreshToken") or body.get("refresh_token")

    if not isinstance(raw_token, str) or not raw_token.strip():
        raise AppError("INVALID_REQUEST", 400, "refreshToken is required.")

    service = _get_auth_service(request)
    req = RefreshRequest(refresh_token=raw_token.strip())
    result = await service.refresh(req.refresh_token, _get_request_id(request))
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    """Revoke the supplied refresh token (no-op if already revoked)."""
    # Logout is best-effort: parse body but don't fail if token is missing
    try:
        body = await request.json()
    except Exception:
        body = {}

    raw_token = (body or {}).get("refreshToken") or (body or {}).get("refresh_token")

    if isinstance(raw_token, str) and raw_token.strip():
        service = _get_auth_service(request)
        await service.logout(raw_token.strip())

    result = LogoutResponse(success=True, request_id=_get_request_id(request))
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me  [requires auth]
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_profile(request: Request) -> JSONResponse:
    """Return the authenticated user's profile. Requires Bearer token."""
    user_id = _get_user_id(request)
    service = _get_auth_service(request)
    user = await service.get_user_by_id(user_id)
    if not user or user.deleted_at is not None:
        raise AppError("UNAUTHORIZED", 401, "User not found.")

    from src.schemas.auth import UserProfile

    result = ProfileResponse(
        success=True,
        user=UserProfile(id=user.id, email=user.email, created_at=user.created_at),
        request_id=_get_request_id(request),
    )
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/auth/me  [requires auth]
# ---------------------------------------------------------------------------


@router.delete("/me")
async def delete_account(request: Request) -> JSONResponse:
    """Soft-delete the authenticated user account and revoke all sessions."""
    user_id = _get_user_id(request)
    service = _get_auth_service(request)
    await service.delete_account(user_id)

    result = DeleteAccountResponse(
        success=True,
        message="Your account has been deleted.",
        request_id=_get_request_id(request),
    )
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/auth/migrate-session  [requires auth]
# ---------------------------------------------------------------------------


@router.post("/migrate-session")
async def migrate_session(request: Request) -> JSONResponse:
    """Re-own anonymous conversations created under a session_id to the authenticated user.

    This is a one-way migration: anonymous conversations (user_id IS NULL) whose
    session_id matches the supplied value are assigned to the current user_id.
    """
    user_id = _get_user_id(request)
    body = await _parse_json_body(request)
    session_id = body.get("sessionId") or body.get("session_id")

    if not isinstance(session_id, str) or not session_id.strip():
        raise AppError("INVALID_REQUEST", 400, "sessionId is required.")

    req = MigrateSessionRequest(session_id=session_id.strip())

    # Perform migration directly against D1 (no service layer needed — pure SQL)
    migrated_count = 0
    db = getattr(request.state, "db", None)
    if db is not None:
        stmt = db.prepare(
            """
            UPDATE conversations
            SET user_id = ?
            WHERE session_id = ? AND user_id IS NULL
            """
        ).bind(user_id, req.session_id)
        res = await stmt.run()
        meta = res.get("meta", {}) if isinstance(res, dict) else (getattr(res, "meta", {}) or {})
        migrated_count = meta.get("changes", 0) if isinstance(meta, dict) else 0

    result = MigrateSessionResponse(
        success=True,
        migrated_count=migrated_count,
        request_id=_get_request_id(request),
    )
    return JSONResponse(
        status_code=200,
        content=result.model_dump(by_alias=True, exclude_none=True),
    )
