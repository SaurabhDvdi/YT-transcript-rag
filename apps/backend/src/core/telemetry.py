"""Structured JSON logging, request correlation, and operational telemetry."""

import json
import logging
from datetime import UTC, datetime

from src.schemas.telemetry import SystemMetricsSummary

logger = logging.getLogger("api")


class TelemetryService:
    """Central operational telemetry collector and metrics aggregator."""

    _instance: "TelemetryService | None" = None

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.rate_limited_requests: int = 0
        self.quota_exceeded_requests: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self._latencies: list[float] = []

    @classmethod
    def get_instance(cls) -> "TelemetryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str = "unknown",
        session_id: str | None = None,
        video_id: str | None = None,
    ) -> None:
        self.total_requests += 1
        if status_code >= 400:
            self.total_errors += 1
        if status_code == 429:
            self.rate_limited_requests += 1

        self._latencies.append(duration_ms)
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

        log_payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "INFO" if status_code < 400 else ("WARN" if status_code < 500 else "ERROR"),
            "event": "http_request",
            "method": method,
            "path": path,
            "statusCode": status_code,
            "durationMs": round(duration_ms, 2),
            "requestId": request_id,
            "sessionId": session_id,
            "videoId": video_id,
        }
        # Structured single-line JSON log (zero secrets, transcripts, or prompts)
        logger.info(json.dumps({k: v for k, v in log_payload.items() if v is not None}))

    def record_cache_hit(self) -> None:
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        self.cache_misses += 1

    def record_quota_exceeded(self) -> None:
        self.quota_exceeded_requests += 1

    def get_metrics_summary(self) -> SystemMetricsSummary:
        avg_lat = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        return SystemMetricsSummary(
            total_requests=self.total_requests,
            total_errors=self.total_errors,
            rate_limited_requests=self.rate_limited_requests,
            quota_exceeded_requests=self.quota_exceeded_requests,
            cache_hits=self.cache_hits,
            cache_misses=self.cache_misses,
            avg_latency_ms=round(avg_lat, 2),
        )

    def reset(self) -> None:
        self.total_requests = 0
        self.total_errors = 0
        self.rate_limited_requests = 0
        self.quota_exceeded_requests = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self._latencies.clear()
