"""Domain errors and application exception definitions."""

from typing import Literal

ApiErrorCode = Literal[
    "INVALID_REQUEST",
    "INVALID_VIDEO_ID",
    "NOT_FOUND",
    "TRANSCRIPT_UNAVAILABLE",
    "TRANSCRIPT_PARSE_ERROR",
    "TRANSCRIPT_TOO_SHORT",
    "RETRIEVAL_NOT_READY",
    "INVALID_QUERY",
    "INVALID_TOP_K",
    "INVALID_QUESTION",
    "LLM_PROVIDER_ERROR",
    "LLM_OUTPUT_INVALID",
    "LLM_TIMEOUT",
    "CONVERSATION_NOT_FOUND",
    "INVALID_CONVERSATION_ID",
    "CONVERSATION_VIDEO_MISMATCH",
    "CONVERSATION_FORBIDDEN",
    "RATE_LIMIT_EXCEEDED",
    "RATE_LIMITED",
    "QUOTA_EXCEEDED",
    "JOB_FAILED",
    "JOB_NOT_FOUND",
    "SERVICE_UNAVAILABLE",
    "CONCURRENT_STREAM_LIMIT_EXCEEDED",
    "INTERNAL_ERROR",
    "METHOD_NOT_ALLOWED",
    "STREAM_INTERRUPTED",
    "STREAM_TIMEOUT",
    "STREAM_ABORTED",
    # Auth
    "UNAUTHORIZED",
    "EMAIL_ALREADY_EXISTS",
    "INVALID_CREDENTIALS",
    "ACCOUNT_DELETED",
    "SESSION_EXPIRED",
    "SESSION_REVOKED",
    "INVALID_EMAIL",
    "INVALID_PASSWORD",
    "FORBIDDEN",
]


class AppError(Exception):
    """Domain-specific application error mapped to a structured ApiErrorResponse."""

    def __init__(self, code: ApiErrorCode | str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
