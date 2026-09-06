"""Access-token and refresh-token lifecycle.

Access token format (no JWT library required):
    base64url(json_payload) + "." + hmac_sha256_hex(base64url(json_payload))

Refresh token:
    A 32-byte cryptographically-random hex string.
    Only its SHA-256 hash is stored in D1.
"""

import base64
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.services.auth.crypto import sha256_hex, sign_payload, verify_signature

# ---------------------------------------------------------------------------
# Access token
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserTokenClaims:
    user_id: str
    email: str
    issued_at: int  # Unix timestamp
    expires_at: int  # Unix timestamp


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_access_token(
    user_id: str,
    email: str,
    secret: str,
    ttl_seconds: int = 900,
) -> str:
    """Create a signed opaque access token.

    Format:  ``<b64url(payload_json)>.<hmac_hex>``

    Args:
        user_id: UUID of the authenticated user.
        email: User's email (embedded for convenience).
        secret: HMAC signing secret from config.
        ttl_seconds: Token lifetime in seconds (default 15 min).

    Returns:
        Signed token string.
    """
    now = int(datetime.now(UTC).timestamp())
    payload = {
        "uid": user_id,
        "email": email,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)
    signature = sign_payload(payload_b64.encode("ascii"), secret)
    return f"{payload_b64}.{signature}"


def decode_access_token(token: str, secret: str) -> UserTokenClaims | None:
    """Decode and verify an access token.

    Returns ``UserTokenClaims`` if the token is valid and not expired,
    ``None`` otherwise (invalid signature, malformed, or expired).
    """
    try:
        payload_b64, signature = token.rsplit(".", 1)
    except ValueError:
        return None

    if not verify_signature(payload_b64.encode("ascii"), signature, secret):
        return None

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None

    now = int(datetime.now(UTC).timestamp())
    if payload.get("exp", 0) <= now:
        return None

    return UserTokenClaims(
        user_id=payload["uid"],
        email=payload["email"],
        issued_at=payload["iat"],
        expires_at=payload["exp"],
    )


# ---------------------------------------------------------------------------
# Refresh token
# ---------------------------------------------------------------------------


def create_refresh_token() -> tuple[str, str]:
    """Generate a new refresh token.

    Returns:
        ``(token_hex, sha256_hash_hex)`` — the raw token is sent to the client;
        only the hash is stored server-side.
    """
    raw = secrets.token_hex(32)
    token_hash = sha256_hex(raw)
    return raw, token_hash


def hash_refresh_token(raw_token: str) -> str:
    """Return the SHA-256 hex hash of a raw refresh token."""
    return sha256_hex(raw_token)


def refresh_token_expires_at(ttl_days: int = 30) -> str:
    """Return ISO-8601 UTC expiry timestamp for a new refresh token."""
    return (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat()
