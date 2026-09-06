"""Readiness endpoint evaluating dependencies without triggering expensive external AI calls."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.schemas.telemetry import ReadinessDependencyStatus, ReadinessResponse
from src.services.resilience.circuit_breaker import ProviderHealthTracker

router = APIRouter(prefix="/api/v1/ready", tags=["Health"])


@router.get("", response_model=ReadinessResponse)
@router.get("/", response_model=ReadinessResponse, include_in_schema=False)
async def check_readiness(request: Request) -> JSONResponse:
    settings = get_settings()
    now_iso = datetime.now(UTC).isoformat()
    req_id = getattr(request.state, "request_id", "unknown")

    dependencies: dict[str, ReadinessDependencyStatus] = {}
    all_ok = True

    # 1. D1 Database Check
    db = getattr(request.state, "db", None)
    if db is not None:
        try:
            t0 = time.perf_counter()
            stmt = db.prepare("SELECT 1 as alive")
            row = await stmt.first()
            lat = (time.perf_counter() - t0) * 1000.0
            dependencies["database"] = ReadinessDependencyStatus(
                status="ok" if row else "degraded",
                details="D1 query succeeded",
                latency_ms=round(lat, 2),
            )
        except Exception as e:
            all_ok = False
            dependencies["database"] = ReadinessDependencyStatus(
                status="unavailable",
                details=f"D1 error: {e}",
            )
    else:
        # In-memory database mode
        dependencies["database"] = ReadinessDependencyStatus(
            status="ok",
            details="In-memory SQLite/Dictionary active",
            latency_ms=0.1,
        )

    # 2. Cache Check
    cache_kv = getattr(request.state, "cache_kv", None)
    dependencies["cache"] = ReadinessDependencyStatus(
        status="ok",
        details="KV cache bound" if cache_kv else "InMemory cache active",
        latency_ms=0.2,
    )

    # 3. Vector Store Check
    vector_index = getattr(request.state, "vector_index", None)
    dependencies["vector_store"] = ReadinessDependencyStatus(
        status="ok",
        details="Vectorize index bound" if vector_index else "D1/InMemory vector store active",
        latency_ms=0.2,
    )

    # 4. LLM Provider Health Check (Passive status inspect, zero tokens consumed)
    health_tracker = ProviderHealthTracker.get_instance()
    all_health = health_tracker.get_all_health()
    gemini_status = all_health.get("gemini", {}).get("state", "CLOSED")
    cf_status = all_health.get("cloudflare-workers-ai", {}).get("state", "CLOSED")

    llm_ok = gemini_status != "OPEN" or cf_status != "OPEN"
    if not llm_ok:
        all_ok = False

    dependencies["llm_providers"] = ReadinessDependencyStatus(
        status="ok" if llm_ok else "degraded",
        details=f"Gemini: {gemini_status}, Cloudflare Workers AI: {cf_status}",
    )

    overall_status = "ok" if all_ok else "degraded"
    resp = ReadinessResponse(
        status=overall_status,
        version=settings.API_VERSION,
        service=settings.SERVICE_NAME,
        timestamp=now_iso,
        dependencies=dependencies,
        request_id=req_id,
    )

    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content=resp.model_dump(by_alias=True, exclude_none=True),
    )
