"""Tests for system readiness checks and operational telemetry."""

import pytest
from httpx import AsyncClient

from src.core.telemetry import TelemetryService


@pytest.mark.asyncio
async def test_ready_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dependencies" in data
    assert "version" in data
    assert "service" in data

    deps = data["dependencies"]
    assert "database" in deps
    assert "vector_store" in deps
    assert "llm_providers" in deps
    assert "cache" in deps
    assert deps["database"]["status"] in ("ok", "degraded")


def test_telemetry_service_metrics():
    telem = TelemetryService()

    # Record operations
    telem.record_request("GET", "/api/v1/health", 200, duration_ms=12.5, request_id="req_1")
    telem.record_request("POST", "/api/v1/videos", 400, duration_ms=5.0, request_id="req_2")
    telem.record_request("POST", "/api/v1/videos/v1/ask", 429, duration_ms=2.0, request_id="req_3")
    telem.record_cache_hit()
    telem.record_cache_miss()
    telem.record_quota_exceeded()

    summary = telem.get_metrics_summary()
    assert summary.total_requests == 3
    assert summary.total_errors == 2  # 400 and 429 are >= 400
    assert summary.rate_limited_requests == 1
    assert summary.quota_exceeded_requests == 1
    assert summary.cache_hits == 1
    assert summary.cache_misses == 1
    assert summary.avg_latency_ms > 0
