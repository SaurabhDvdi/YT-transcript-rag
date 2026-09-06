"""ASGI middlewares: CORS, Request ID, Rate Limiting, and Structured Logging."""

import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.core.config import get_settings
from src.services.auth.crypto import verify_signature
from src.services.auth.tokens import _b64url_decode, decode_access_token

SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{6,64}$")
logger = logging.getLogger("api")

# Rate limit sliding-window store: ip -> [count, reset_at_timestamp_ms]
_ip_buckets: dict[str, list[float]] = {}


def reset_rate_limit_store() -> None:
    """Reset rate limit store for unit testing."""
    _ip_buckets.clear()


def is_allowed_origin(
    origin: str | None,
    configured_origins: str | None = None,
    environment: str = "development",
) -> bool:
    """Validates if an incoming Origin is an allowed extension or local development origin."""
    if not origin:
        return False

    # 1. Browser extension origins
    if origin.startswith("chrome-extension://") or origin.startswith("moz-extension://"):
        return True

    # 2. Local development origins (only permitted in non-production environments)
    if environment != "production" and (
        origin.startswith("http://localhost:")
        or origin == "http://localhost"
        or origin.startswith("http://127.0.0.1:")
        or origin == "http://127.0.0.1"
    ):
        return True

    # 3. Configured explicit origins
    if configured_origins:
        patterns = [p.strip() for p in configured_origins.split(",") if p.strip()]
        for pattern in patterns:
            if pattern == "*":
                if environment == "production":
                    continue  # Prohibit wildcard CORS in production
                return True
            if pattern.endswith("*") and origin.startswith(pattern[:-1]):
                return True
            if pattern == origin:
                return True

    return False


_AUTH_ERRORS: dict[str, str] = {
    "UNAUTHORIZED": "Authentication required. Please provide a valid Bearer token.",
    "SESSION_EXPIRED": "Access token has expired. Please refresh your session.",
    "SESSION_REVOKED": "Access token is invalid.",
}


class ApiGatewayMiddleware:
    """Composite pure-ASGI middleware handling Request ID, CORS, Rate Limiting, and Logging.

    Pure ASGI avoids Starlette BaseHTTPMiddleware streaming response buffering issues.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_ms: int = 60_000,
    ) -> None:
        self.app = app
        self.max_requests = max_requests
        self.window_ms = window_ms

    async def _resolve_bearer(self, scope: Scope, raw_token: str) -> str | None:
        """Validate a Bearer access token and inject user_id into scope state.

        Returns:
            None if the token is valid (user_id injected).
            An error code string if the token is invalid.
        """
        settings = get_settings()
        claims = decode_access_token(raw_token, settings.auth_token_secret)
        if claims is None:
            # Distinguish expired token from invalid/tampered token
            try:
                payload_b64, signature = raw_token.rsplit(".", 1)
                if verify_signature(
                    payload_b64.encode("ascii"), signature, settings.auth_token_secret
                ):
                    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
                    now = int(datetime.now(UTC).timestamp())
                    if payload.get("exp", 0) <= now:
                        return "SESSION_EXPIRED"
            except Exception:
                pass
            return "UNAUTHORIZED"

        state = scope.get("state")
        if isinstance(state, dict):
            state["user_id"] = claims.user_id
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        start_time = time.time()

        # 1. Request ID and Session ID resolution
        incoming_req_id = headers.get("x-request-id", "").strip()
        if incoming_req_id and SAFE_REQUEST_ID_REGEX.match(incoming_req_id):
            request_id = incoming_req_id
        else:
            request_id = str(uuid.uuid4())

        incoming_session_id = headers.get("x-session-id", "").strip()
        session_id = incoming_session_id if incoming_session_id else str(uuid.uuid4())

        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["request_id"] = request_id
        scope["state"]["session_id"] = session_id
        scope["state"]["user_id"] = None  # populated below if Bearer token is valid

        # Content-Length check (1 MB maximum body size limit for abuse prevention)
        MAX_BODY_BYTES = 1_048_576  # 1 MB
        content_length_hdr = headers.get("content-length")
        if content_length_hdr:
            try:
                if int(content_length_hdr) > MAX_BODY_BYTES:
                    err_body = json.dumps(
                        {
                            "success": False,
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": "Request payload exceeds 1MB limit.",
                            },
                            "requestId": request_id,
                        }
                    ).encode("utf-8")
                    resp_headers: list[tuple[bytes, bytes]] = [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(err_body)).encode("utf-8")),
                        (b"x-request-id", request_id.encode("utf-8")),
                    ]
                    await send(
                        {"type": "http.response.start", "status": 413, "headers": resp_headers}
                    )
                    await send({"type": "http.response.body", "body": err_body})
                    return
            except ValueError:
                pass

        # Bind resources from Workers env if present
        env = scope.get("env")
        if env is not None:
            scope["state"]["db"] = getattr(env, "DB", None)
            scope["state"]["cache_kv"] = getattr(env, "CACHE_KV", None)
            scope["state"]["vector_index"] = getattr(env, "VECTOR_INDEX", None)
            scope["state"]["rate_limiter"] = getattr(env, "RATE_LIMITER", None)

        # --- Optional Bearer token auth ---
        # If Authorization header is present we MUST validate it.
        # A missing header is fine (anonymous path). A present-but-invalid header → 401.
        auth_header = headers.get("authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            raw_token = auth_header[7:].strip()
            bearer_err = await self._resolve_bearer(scope, raw_token)
            if bearer_err is not None:
                # Return 401 immediately without proceeding to the application
                origin = headers.get("origin")
                settings_for_cors = get_settings()
                allowed_cors = is_allowed_origin(
                    origin, settings_for_cors.ALLOWED_ORIGINS, settings_for_cors.environment
                )
                err_body = json.dumps(
                    {
                        "success": False,
                        "error": {"code": bearer_err, "message": _AUTH_ERRORS[bearer_err]},
                        "requestId": request_id,
                    }
                ).encode("utf-8")
                resp_headers = [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(err_body)).encode()),
                    (b"x-request-id", request_id.encode()),
                ]
                if allowed_cors and origin:
                    resp_headers.extend(
                        [
                            (b"access-control-allow-origin", origin.encode()),
                            (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
                            (
                                b"access-control-allow-headers",
                                b"Content-Type, X-Request-ID, X-Session-ID, X-Admin-Key, Authorization",
                            ),
                            (b"vary", b"Origin"),
                        ]
                    )
                await send({"type": "http.response.start", "status": 401, "headers": resp_headers})
                await send({"type": "http.response.body", "body": err_body})
                return

        # 2. CORS check
        origin = headers.get("origin")
        settings = get_settings()
        allowed = is_allowed_origin(origin, settings.ALLOWED_ORIGINS, settings.environment)

        # Handle Preflight OPTIONS
        if scope["method"] == "OPTIONS":
            cors_headers: list[tuple[bytes, bytes]] = [
                (b"content-length", b"0"),
                (b"x-request-id", request_id.encode("utf-8")),
                (b"x-session-id", session_id.encode("utf-8")),
            ]
            if allowed and origin:
                cors_headers.extend(
                    [
                        (b"access-control-allow-origin", origin.encode("utf-8")),
                        (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
                        (
                            b"access-control-allow-headers",
                            b"Content-Type, X-Request-ID, X-Session-ID, X-Admin-Key, Authorization",
                        ),
                        (b"access-control-max-age", b"86400"),
                        (b"vary", b"Origin"),
                    ]
                )
            await send({"type": "http.response.start", "status": 204, "headers": cors_headers})
            await send({"type": "http.response.body", "body": b""})
            return

        # 3. Multi-dimensional Rate Limiting check
        client_ip = (
            headers.get("cf-connecting-ip")
            or (
                headers.get("x-forwarded-for", "").split(",")[0].strip()
                if headers.get("x-forwarded-for")
                else None
            )
            or (scope.get("client", ["127.0.0.1"])[0] if scope.get("client") else "127.0.0.1")
        )

        path = scope.get("path", "")
        # Multi-dimensional limits per endpoint tier
        if "/auth/login" in path or "/auth/register" in path:
            max_reqs = 10
            endpoint_key = "auth-mut"
        elif "/ask" in path:
            max_reqs = 30
            endpoint_key = "ask"
        elif "/retrieval" in path:
            max_reqs = 50
            endpoint_key = "retrieval"
        elif "/health" in path or "/ready" in path:
            max_reqs = self.max_requests  # Default 100
            endpoint_key = "health"
        else:
            max_reqs = self.max_requests
            endpoint_key = path.split("/")[3] if len(path.split("/")) > 3 else "root"

        now_ms = time.time() * 1000.0
        rate_key = f"{client_ip}:{endpoint_key}"
        bucket = _ip_buckets.get(rate_key)

        if not bucket or now_ms >= bucket[1]:
            bucket = [1.0, now_ms + self.window_ms]
            _ip_buckets[rate_key] = bucket
        else:
            bucket[0] += 1.0

        count = int(bucket[0])
        remaining = max(0, max_reqs - count)
        retry_after_sec = max(1, int((bucket[1] - now_ms) / 1000.0))

        rate_limit_headers = [
            (b"x-ratelimit-limit", str(max_reqs).encode("utf-8")),
            (b"x-ratelimit-remaining", str(remaining).encode("utf-8")),
            (b"x-session-id", session_id.encode("utf-8")),
        ]

        if count > max_reqs:
            rate_limit_headers.append((b"retry-after", str(retry_after_sec).encode("utf-8")))
            err_body = json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Please try again later.",
                    },
                    "requestId": request_id,
                }
            ).encode("utf-8")

            resp_headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(err_body)).encode("utf-8")),
                (b"x-request-id", request_id.encode("utf-8")),
            ] + rate_limit_headers

            if allowed and origin:
                resp_headers.extend(
                    [
                        (b"access-control-allow-origin", origin.encode("utf-8")),
                        (b"access-control-allow-methods", b"GET, POST, PATCH, DELETE, OPTIONS"),
                        (
                            b"access-control-allow-headers",
                            b"Content-Type, X-Request-ID, Authorization",
                        ),
                        (b"access-control-max-age", b"86400"),
                        (b"vary", b"Origin"),
                    ]
                )

            await send({"type": "http.response.start", "status": 429, "headers": resp_headers})
            await send({"type": "http.response.body", "body": err_body})
            return

        status_code = [200]

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
                mut_headers = MutableHeaders(raw=message.setdefault("headers", []))
                mut_headers["x-request-id"] = request_id
                mut_headers["x-session-id"] = session_id
                mut_headers["x-ratelimit-limit"] = str(max_reqs)
                mut_headers["x-ratelimit-remaining"] = str(remaining)
                mut_headers["x-content-type-options"] = "nosniff"
                mut_headers["x-frame-options"] = "DENY"

                # Prevent caching of sensitive and authenticated routes
                if any(p in path for p in ("/auth", "/conversations", "/ask", "/admin")):
                    mut_headers["cache-control"] = "no-store, no-cache, must-revalidate, private"
                    mut_headers["pragma"] = "no-cache"

                if allowed and origin:
                    mut_headers["access-control-allow-origin"] = origin
                    mut_headers["access-control-allow-methods"] = (
                        "GET, POST, PATCH, DELETE, OPTIONS"
                    )
                    mut_headers["access-control-allow-headers"] = (
                        "Content-Type, X-Request-ID, X-Session-ID, X-Admin-Key, Authorization"
                    )
                    mut_headers["access-control-max-age"] = "86400"
                    mut_headers["vary"] = "Origin"

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = float((time.time() - start_time) * 1000.0)
            status = status_code[0]
            from src.core.telemetry import TelemetryService

            TelemetryService.get_instance().record_request(
                method=scope.get("method", "UNKNOWN"),
                path=scope.get("path", "/"),
                status_code=status,
                duration_ms=duration_ms,
                request_id=request_id,
                session_id=session_id,
            )
