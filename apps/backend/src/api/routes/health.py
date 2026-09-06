"""Health endpoint returning service status and version."""

from fastapi import APIRouter

from src.core.config import get_settings
from src.schemas.health import HealthResponse

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
@router.get("/", response_model=HealthResponse, include_in_schema=False)
async def get_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.SERVICE_NAME,
        version=settings.API_VERSION,
    )
