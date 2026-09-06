"""Unit and integration tests for AuthService using InMemoryAuthRepository."""

import pytest

from src.core.errors import AppError
from src.repositories.auth import InMemoryAuthRepository
from src.services.auth.service import AuthService


@pytest.fixture
def auth_service() -> AuthService:
    repo = InMemoryAuthRepository()
    return AuthService(repo=repo)


class TestRegister:
    async def test_successful_registration(self, auth_service: AuthService) -> None:
        resp = await auth_service.register("test@example.com", "securepassword123")
        assert resp.success is True
        assert resp.user.email == "test@example.com"
        assert resp.tokens.access_token is not None
        assert resp.tokens.refresh_token is not None
        assert resp.tokens.token_type.lower() == "bearer"

    async def test_case_insensitive_email(self, auth_service: AuthService) -> None:
        resp1 = await auth_service.register("TestUser@Example.COM", "securepassword123")
        assert resp1.user.email == "testuser@example.com"

        with pytest.raises(AppError) as exc_info:
            await auth_service.register("testuser@example.com", "otherpassword123")
        assert exc_info.value.code == "EMAIL_ALREADY_EXISTS"
        assert exc_info.value.status_code == 409

    async def test_invalid_email_format(self, auth_service: AuthService) -> None:
        with pytest.raises(AppError) as exc_info:
            await auth_service.register("not-an-email", "securepassword123")
        assert exc_info.value.code == "INVALID_EMAIL"
        assert exc_info.value.status_code == 422

    async def test_short_password(self, auth_service: AuthService) -> None:
        with pytest.raises(AppError) as exc_info:
            await auth_service.register("user@example.com", "short")
        assert exc_info.value.code == "INVALID_PASSWORD"
        assert exc_info.value.status_code == 422


class TestLogin:
    async def test_successful_login(self, auth_service: AuthService) -> None:
        await auth_service.register("user@example.com", "password123")
        resp = await auth_service.login("user@example.com", "password123")
        assert resp.success is True
        assert resp.user.email == "user@example.com"
        assert resp.tokens.access_token is not None

    async def test_wrong_password(self, auth_service: AuthService) -> None:
        await auth_service.register("user@example.com", "password123")
        with pytest.raises(AppError) as exc_info:
            await auth_service.login("user@example.com", "wrongpassword")
        assert exc_info.value.code == "INVALID_CREDENTIALS"
        assert exc_info.value.status_code == 401

    async def test_unknown_email(self, auth_service: AuthService) -> None:
        with pytest.raises(AppError) as exc_info:
            await auth_service.login("nonexistent@example.com", "password123")
        assert exc_info.value.code == "INVALID_CREDENTIALS"
        assert exc_info.value.status_code == 401


class TestRefresh:
    async def test_successful_refresh_and_rotation(self, auth_service: AuthService) -> None:
        reg = await auth_service.register("user@example.com", "password123")
        old_refresh = reg.tokens.refresh_token

        refreshed = await auth_service.refresh(old_refresh)
        assert refreshed.success is True
        assert refreshed.tokens.access_token is not None
        assert refreshed.tokens.refresh_token != old_refresh

        # Old refresh token is rotated out and should no longer be usable
        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh(old_refresh)
        assert exc_info.value.code == "SESSION_REVOKED"

    async def test_invalid_refresh_token(self, auth_service: AuthService) -> None:
        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh("completely_fake_refresh_token")
        assert exc_info.value.code == "SESSION_REVOKED"


class TestLogoutAndDeletion:
    async def test_logout_revokes_session(self, auth_service: AuthService) -> None:
        reg = await auth_service.register("user@example.com", "password123")
        refresh_token = reg.tokens.refresh_token

        await auth_service.logout(refresh_token)

        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh(refresh_token)
        assert exc_info.value.code == "SESSION_REVOKED"

    async def test_delete_account_blocks_login_and_refresh(self, auth_service: AuthService) -> None:
        reg = await auth_service.register("user@example.com", "password123")
        user_id = reg.user.id
        refresh_token = reg.tokens.refresh_token

        await auth_service.delete_account(user_id)

        # Login blocked
        with pytest.raises(AppError) as exc_info:
            await auth_service.login("user@example.com", "password123")
        assert exc_info.value.code == "ACCOUNT_DELETED"

        # Refresh blocked
        with pytest.raises(AppError) as exc_info:
            await auth_service.refresh(refresh_token)
        assert exc_info.value.code == "SESSION_REVOKED"
