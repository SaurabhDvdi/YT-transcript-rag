"""Security tests: Authentication, timing safety, token tampering, and replay protection."""

import pytest
from httpx import AsyncClient

from src.core.config import Settings, validate_production_settings
from src.core.errors import AppError
from src.services.auth.service import AuthService
from src.services.auth.tokens import create_access_token


@pytest.mark.asyncio
async def test_auth_login_constant_time_nonexistent_user(monkeypatch):
    """Ensure non-existent user login executes PBKDF2 dummy verification to prevent timing attacks."""
    auth_svc = AuthService()
    dummy_called = False

    import src.services.auth.service as auth_mod

    original_verify = auth_mod.verify_password

    def mock_verify(password, salt, stored_hash):
        nonlocal dummy_called
        if salt == auth_mod._DUMMY_SALT:
            dummy_called = True
        return original_verify(password, salt, stored_hash)

    monkeypatch.setattr(auth_mod, "verify_password", mock_verify)

    with pytest.raises(AppError) as exc_info:
        await auth_svc.login("nonexistent@example.com", "Password123!")

    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert dummy_called is True, "Dummy PBKDF2 verification was not executed for non-existent user"


@pytest.mark.asyncio
async def test_access_token_tampering(async_client: AsyncClient):
    """Tampered token signatures or payloads must be rejected with 401 UNAUTHORIZED."""
    # Register a legitimate user
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "tamper@example.com", "password": "StrongPassword123!"},
    )
    assert reg.status_code == 201
    valid_token = reg.json()["tokens"]["accessToken"]

    # 1. Modify the payload portion (first segment of base64url token)
    parts = valid_token.split(".")
    assert len(parts) == 2
    tampered_token = f"eyJhZG1pbiI6dHJ1ZX0.{parts[1]}"

    res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res.status_code == 401
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNAUTHORIZED"

    # 2. Corrupt the signature segment
    corrupted_sig = f"{parts[0]}.{parts[1]}.bad_signature"
    res2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {corrupted_sig}"},
    )
    assert res2.status_code == 401
    assert res2.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_expired_access_token(async_client: AsyncClient):
    """Expired access token must return 401 with SESSION_EXPIRED code."""
    # Create an expired token manually with negative TTL
    expired_token = create_access_token(
        user_id="usr-123",
        email="expired@example.com",
        secret="dev-insecure-secret-change-in-prod-32chars",
        ttl_seconds=-10,
    )

    res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "SESSION_EXPIRED"


@pytest.mark.asyncio
async def test_refresh_token_replay_attack_revokes_all_sessions(async_client: AsyncClient):
    """Replaying an already rotated refresh token must trigger active defense:
    all user sessions are revoked, and the user must re-authenticate.
    """
    # 1. Register
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "replay_victim@example.com", "password": "SecurePassword123!"},
    )
    r1 = reg.json()["tokens"]["refreshToken"]
    a1 = reg.json()["tokens"]["accessToken"]
    assert a1

    # 2. Valid refresh rotation (r1 -> r2)
    rot = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": r1},
    )
    assert rot.status_code == 200
    r2 = rot.json()["tokens"]["refreshToken"]
    a2 = rot.json()["tokens"]["accessToken"]
    assert a2

    # 3. Attacker replays stolen r1 (which was already revoked)
    replay = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": r1},
    )
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "SESSION_REVOKED"

    # 4. Active defense: r2 must NOW also be revoked due to the detected replay attack!
    rot_after_replay = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": r2},
    )
    assert rot_after_replay.status_code == 401
    assert rot_after_replay.json()["error"]["code"] == "SESSION_REVOKED"


def test_production_config_validation():
    """Production configuration validator must flag insecure development settings."""
    # Insecure default dev settings
    dev_settings = Settings(
        environment="production",
        auth_token_secret="dev-insecure-secret-change-in-prod-32chars",
        admin_api_key="yt-ai-admin-secret",
        allowed_origins="*",
        gemini_api_key=None,
        cf_account_id=None,
        cf_api_token=None,
    )
    issues = validate_production_settings(dev_settings)
    assert len(issues) >= 4
    assert any("AUTH_TOKEN_SECRET" in i for i in issues)
    assert any("ADMIN_API_KEY" in i for i in issues)
    assert any("Wildcard" in i for i in issues)
    assert any("AI provider" in i for i in issues)

    # Secure production settings
    prod_settings = Settings(
        environment="production",
        auth_token_secret="a" * 64,
        admin_api_key="b" * 32,
        allowed_origins="chrome-extension://abcdefghijklmnopqrstuvwxyz123456",
        gemini_api_key="actual_gemini_key",
    )
    assert validate_production_settings(prod_settings) == []
