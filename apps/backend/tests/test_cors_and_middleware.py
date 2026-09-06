"""Tests for CORS, Request ID, and Rate Limiting middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_for_chrome_extension(async_client: AsyncClient):
    headers = {
        "Origin": "chrome-extension://abcdefghijklmnopqrstuvwxyz123456",
        "Access-Control-Request-Method": "POST",
    }
    response = await async_client.options("/api/v1/videos", headers=headers)
    assert response.status_code == 204
    assert (
        response.headers["access-control-allow-origin"]
        == "chrome-extension://abcdefghijklmnopqrstuvwxyz123456"
    )
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


@pytest.mark.asyncio
async def test_cors_preflight_for_firefox_extension(async_client: AsyncClient):
    headers = {
        "Origin": "moz-extension://12345678-1234-1234-1234-123456789abc",
        "Access-Control-Request-Method": "GET",
    }
    response = await async_client.options("/api/v1/health", headers=headers)
    assert response.status_code == 204
    assert (
        response.headers["access-control-allow-origin"]
        == "moz-extension://12345678-1234-1234-1234-123456789abc"
    )


@pytest.mark.asyncio
async def test_cors_headers_on_standard_request(async_client: AsyncClient):
    headers = {"Origin": "http://localhost:5173"}
    response = await async_client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_request_id_echo(async_client: AsyncClient):
    custom_id = "test-request-id-12345"
    response = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == custom_id


@pytest.mark.asyncio
async def test_request_id_auto_generated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) >= 6


@pytest.mark.asyncio
async def test_rate_limiting_trigger(async_client: AsyncClient):
    # Fire 105 requests rapidly to trigger rate limiting (limit: 100)
    triggered_429 = False
    for _ in range(105):
        resp = await async_client.get(
            "/api/v1/health", headers={"CF-Connecting-IP": "198.51.100.1"}
        )
        if resp.status_code == 429:
            triggered_429 = True
            data = resp.json()
            assert data["success"] is False
            assert data["error"]["code"] == "RATE_LIMITED"
            assert "retry-after" in resp.headers
            break

    assert triggered_429 is True
