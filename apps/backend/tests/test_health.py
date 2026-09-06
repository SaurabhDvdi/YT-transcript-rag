"""Tests for GET /api/v1/health."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "youtube-ai-api"
    assert "version" in data
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_health_with_trailing_slash(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
