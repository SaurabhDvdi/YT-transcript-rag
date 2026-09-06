"""Telemetry, health, and readiness schemas."""

from src.schemas.base import CamelModel


class ReadinessDependencyStatus(CamelModel):
    status: str  # "ok" | "degraded" | "unavailable"
    details: str | None = None
    latency_ms: float | None = None


class ReadinessResponse(CamelModel):
    status: str  # "ok" | "degraded" | "unavailable"
    version: str
    service: str
    timestamp: str
    dependencies: dict[str, ReadinessDependencyStatus]
    request_id: str | None = None


class SystemMetricsSummary(CamelModel):
    total_requests: int = 0
    total_errors: int = 0
    rate_limited_requests: int = 0
    quota_exceeded_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_latency_ms: float = 0.0
