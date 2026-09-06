"""FastAPI Application setup and exception handlers."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.middleware import ApiGatewayMiddleware
from src.api.routes.admin import router as admin_router
from src.api.routes.auth import router as auth_router
from src.api.routes.conversations import router as conversations_router
from src.api.routes.health import router as health_router
from src.api.routes.ready import router as ready_router
from src.api.routes.videos import router as videos_router
from src.core.config import get_settings
from src.core.errors import AppError

logger = logging.getLogger("api")


def _get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def create_app() -> FastAPI:
    """Factory creating configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. Mount Subsystem Routers
    app.include_router(health_router)
    app.include_router(ready_router)
    app.include_router(auth_router)
    app.include_router(videos_router)
    app.include_router(conversations_router)
    app.include_router(admin_router)

    # 2. Exception Handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
                "requestId": _get_request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Malformed or invalid request payload.",
                },
                "requestId": _get_request_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        req_id = _get_request_id(request)
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"The requested endpoint '{request.method} {request.url.path}' was not found.",
                    },
                    "requestId": req_id,
                },
            )
        if exc.status_code == 405:
            return JSONResponse(
                status_code=405,
                content={
                    "success": False,
                    "error": {
                        "code": "METHOD_NOT_ALLOWED",
                        "message": f"Method {request.method} not allowed on {request.url.path}.",
                    },
                    "requestId": req_id,
                },
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                },
                "requestId": req_id,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal server error occurred.",
                },
                "requestId": _get_request_id(request),
            },
        )

    # 3. Global Gateway Middleware (CORS, Request-ID, Rate Limiting, Logging)
    app.add_middleware(ApiGatewayMiddleware, max_requests=100, window_ms=60_000)

    return app


app = create_app()
