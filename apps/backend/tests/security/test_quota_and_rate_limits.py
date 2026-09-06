"""Security tests: Rate limiting tiers, CORS restrictions, and abuse prevention."""

import pytest
from httpx import AsyncClient

from src.api.middleware import is_allowed_origin, reset_rate_limit_store


@pytest.mark.asyncio
async def test_auth_endpoint_rate_limiting_tier(async_client: AsyncClient):
    """Auth mutation endpoints (/auth/login) must enforce 10 req/min limit."""
    reset_rate_limit_store()

    client_ip = "192.168.1.100"
    headers = {"CF-Connecting-IP": client_ip}

    # First 10 requests should proceed (failing auth with 401, but not 429)
    for _ in range(10):
        res = await async_client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"email": "brute@example.com", "password": "WrongPassword!"},
        )
        assert res.status_code == 401

    # 11th request must be rate limited (429)
    res_limited = await async_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"email": "brute@example.com", "password": "WrongPassword!"},
    )
    assert res_limited.status_code == 429
    data = res_limited.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RATE_LIMITED"
    assert "retry-after" in res_limited.headers


def test_cors_production_environment_restrictions():
    """Localhost and wildcards must NOT be permitted in production environment."""
    # Development: localhost is permitted
    assert is_allowed_origin("http://localhost:3000", environment="development") is True
    assert is_allowed_origin("http://127.0.0.1:5173", environment="development") is True

    # Production: localhost is forbidden
    assert is_allowed_origin("http://localhost:3000", environment="production") is False
    assert is_allowed_origin("http://127.0.0.1:5173", environment="production") is False

    # Production: wildcard is ignored
    assert (
        is_allowed_origin("https://evil.com", configured_origins="*", environment="production")
        is False
    )

    # Extension origins are always permitted
    assert (
        is_allowed_origin("chrome-extension://abcdefghijklmnop", environment="production") is True
    )
    assert is_allowed_origin("moz-extension://abcdefghijklmnop", environment="production") is True
