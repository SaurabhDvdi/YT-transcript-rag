"""Integration tests for all /api/v1/auth/* endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_registration_lifecycle(async_client: AsyncClient):
    email = "newuser@example.com"
    password = "securePassword123"

    # 1. Register successfully
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert reg_data["success"] is True
    assert reg_data["user"]["email"] == email
    assert "tokens" in reg_data
    access_token = reg_data["tokens"]["accessToken"]
    refresh_token = reg_data["tokens"]["refreshToken"]
    assert access_token is not None
    assert refresh_token is not None

    # 2. Duplicate registration returns 409
    dup_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    # 3. Invalid email format returns 422
    inv_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": password},
    )
    assert inv_resp.status_code == 422
    assert inv_resp.json()["error"]["code"] == "INVALID_EMAIL"

    # 4. Short password returns 422
    short_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "short"},
    )
    assert short_resp.status_code == 422
    assert short_resp.json()["error"]["code"] == "INVALID_PASSWORD"


@pytest.mark.asyncio
async def test_auth_login_lifecycle(async_client: AsyncClient):
    email = "logintest@example.com"
    password = "mySecretPassword1"

    # Register first
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )

    # 1. Successful login
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["success"] is True
    assert login_data["user"]["email"] == email
    assert "accessToken" in login_data["tokens"]

    # 2. Wrong password returns 401
    bad_pw_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword99"},
    )
    assert bad_pw_resp.status_code == 401
    assert bad_pw_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # 3. Non-existent email returns 401
    no_user_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": password},
    )
    assert no_user_resp.status_code == 401
    assert no_user_resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_auth_refresh_rotation(async_client: AsyncClient):
    email = "refreshtest@example.com"
    password = "mySecretPassword2"

    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    old_refresh = reg_resp.json()["tokens"]["refreshToken"]

    # 1. Refresh succeeds
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert refresh_resp.status_code == 200
    refreshed_data = refresh_resp.json()
    new_refresh = refreshed_data["tokens"]["refreshToken"]
    assert new_refresh != old_refresh

    # 2. Old refresh token is revoked (rotation)
    stale_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": old_refresh},
    )
    assert stale_resp.status_code == 401
    assert stale_resp.json()["error"]["code"] == "SESSION_REVOKED"


@pytest.mark.asyncio
async def test_auth_me_and_logout(async_client: AsyncClient):
    email = "metest@example.com"
    password = "mySecretPassword3"

    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    tokens = reg_resp.json()["tokens"]
    access_token = tokens["accessToken"]
    refresh_token = tokens["refreshToken"]

    # 1. Unauthenticated /me returns 401
    unauth_resp = await async_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # 2. Authenticated /me returns profile
    auth_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert auth_resp.status_code == 200
    assert auth_resp.json()["user"]["email"] == email

    # 3. Logout revokes the session
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        json={"refreshToken": refresh_token},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # 4. Refreshing with logged-out refresh token fails
    re_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert re_refresh.status_code == 401


@pytest.mark.asyncio
async def test_delete_account(async_client: AsyncClient):
    email = "deleteme@example.com"
    password = "mySecretPassword4"

    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    tokens = reg_resp.json()["tokens"]
    access_token = tokens["accessToken"]

    # Delete account
    del_resp = await async_client.delete(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Login fails after deletion
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["error"]["code"] == "ACCOUNT_DELETED"
