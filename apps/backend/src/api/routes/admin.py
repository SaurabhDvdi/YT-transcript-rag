"""Admin maintenance endpoints (retention cleanup, orphan detection, stale job recovery)."""

import hmac

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.errors import AppError
from src.services.cleanup.service import CleanupService

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.post("/cleanup")
async def trigger_cleanup(
    request: Request,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
) -> JSONResponse:
    """Triggers operational retention cleanup, stale job recovery, and orphan detection."""
    settings = get_settings()

    # Enforce admin authentication with constant-time comparison
    if (
        not settings.admin_api_key
        or not x_admin_key
        or not hmac.compare_digest(x_admin_key, settings.admin_api_key)
    ):
        raise AppError("UNAUTHORIZED", 401, "Unauthorized: invalid or missing admin key.")

    db = getattr(request.state, "db", None)
    cleanup_svc = CleanupService.get_instance(db)
    results = await cleanup_svc.run_cleanup(db)

    req_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": results,
            "requestId": req_id,
        },
    )
