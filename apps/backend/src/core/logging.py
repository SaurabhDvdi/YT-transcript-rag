"""Structured JSON logging for Cloudflare Workers."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Configure standard root logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
logger = logging.getLogger("youtube-ai-api")


def log_event(
    level: str,
    event: str,
    request_id: str | None = None,
    duration_ms: float | None = None,
    status_code: int | None = None,
    **extra: Any,
) -> None:
    """Emits structured JSON log entry to stdout."""
    payload: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level.lower(),
        "event": event,
    }
    if request_id:
        payload["requestId"] = request_id
    if duration_ms is not None:
        payload["durationMs"] = round(duration_ms, 2)
    if status_code is not None:
        payload["statusCode"] = status_code

    # Sanitize extra fields (avoid logging API keys or prompts)
    for k, v in extra.items():
        if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
            continue
        payload[k] = v

    msg = json.dumps(payload, ensure_ascii=False)
    if level.lower() == "error":
        logger.error(msg)
    elif level.lower() == "warning":
        logger.warning(msg)
    else:
        logger.info(msg)
