"""Error schemas matching ApiErrorResponse envelope."""

from src.schemas.base import CamelModel


class ApiErrorDetail(CamelModel):
    code: str
    message: str


class ApiErrorResponse(CamelModel):
    success: bool = False
    error: ApiErrorDetail
    request_id: str | None = None
