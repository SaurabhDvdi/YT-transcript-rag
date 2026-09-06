"""Health check schemas."""

from src.schemas.base import CamelModel


class HealthResponse(CamelModel):
    status: str = "ok"
    service: str
    version: str
