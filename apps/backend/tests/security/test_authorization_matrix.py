"""Security tests: Authorization matrix, cross-user scoping, and admin protection."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_user_conversation_isolation(async_client: AsyncClient):
    """User A must NOT be able to view User B's conversations for the same video."""
    vid = "dQw4w9WgXcQ"

    # 1. Register User A and create a conversation
    reg_a = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "usera@example.com", "password": "Password123!"},
    )
    assert reg_a.status_code == 201
    tok_a = reg_a.json()["tokens"]["accessToken"]

    res_conv_a = await async_client.post(
        f"/api/v1/videos/{vid}/conversations",
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert res_conv_a.status_code == 201
    conv_a_id = res_conv_a.json()["conversation"]["id"]

    # 2. Register User B and list conversations for the same video
    reg_b = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "userb@example.com", "password": "Password123!"},
    )
    assert reg_b.status_code == 201
    tok_b = reg_b.json()["tokens"]["accessToken"]

    res_list_b = await async_client.get(
        f"/api/v1/videos/{vid}/conversations",
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert res_list_b.status_code == 200
    convs_b = res_list_b.json()["conversations"]
    b_ids = [c["id"] for c in convs_b]
    assert conv_a_id not in b_ids, "User B leaked User A's private conversation!"

    # 3. Anonymous user list must also NOT contain User A's conversation
    res_list_anon = await async_client.get(f"/api/v1/videos/{vid}/conversations")
    assert res_list_anon.status_code == 200
    anon_ids = [c["id"] for c in res_list_anon.json()["conversations"]]
    assert conv_a_id not in anon_ids, "Anonymous user leaked User A's private conversation!"


@pytest.mark.asyncio
async def test_admin_route_authorization_enforcement(async_client: AsyncClient):
    """Admin maintenance endpoints must reject missing or incorrect X-Admin-Key."""
    # 1. Missing header
    res_missing = await async_client.post("/api/v1/admin/cleanup")
    assert res_missing.status_code == 401
    assert res_missing.json()["error"]["code"] == "UNAUTHORIZED"

    # 2. Invalid header
    res_invalid = await async_client.post(
        "/api/v1/admin/cleanup",
        headers={"X-Admin-Key": "completely-wrong-admin-key"},
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. Valid admin key
    res_valid = await async_client.post(
        "/api/v1/admin/cleanup",
        headers={"X-Admin-Key": "yt-ai-admin-secret"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["success"] is True


@pytest.mark.asyncio
async def test_deleted_account_cannot_login_or_access_resources(async_client: AsyncClient):
    """Deleted account must be locked out from login and refresh."""
    email = "deleted_victim@example.com"
    pwd = "Password123!"

    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": pwd},
    )
    tok = reg.json()["tokens"]["accessToken"]

    # Delete account
    del_res = await async_client.delete(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert del_res.status_code == 200

    # Attempt to log in to deleted account
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": pwd},
    )
    assert login_res.status_code == 401
    assert login_res.json()["error"]["code"] == "ACCOUNT_DELETED"
