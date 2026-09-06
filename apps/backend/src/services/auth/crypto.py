"""Pure-stdlib cryptographic primitives for authentication.

No third-party dependencies — everything is hashlib / hmac / secrets.
"""

import hashlib
import hmac
import secrets

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-SHA-256)
# ---------------------------------------------------------------------------

_PBKDF2_ITERATIONS = 600_000
_PBKDF2_HASH = "sha256"
_KEY_LENGTH = 32  # bytes → 64 hex chars


def generate_salt() -> str:
    """Return a cryptographically-random 16-byte salt as a hex string."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """Derive a PBKDF2-SHA-256 password hash.

    Args:
        password: Plain-text password (UTF-8 encoded).
        salt: Hex-encoded 16-byte salt from ``generate_salt()``.

    Returns:
        64-character lowercase hex string.
    """
    dk = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _PBKDF2_ITERATIONS,
        dklen=_KEY_LENGTH,
    )
    return dk.hex()


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    """Constant-time comparison of the supplied password against a stored hash.

    Args:
        password: Plain-text candidate password.
        salt: Salt stored alongside the hash.
        stored_hash: The stored PBKDF2 hash hex string.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.
    """
    candidate = hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


# ---------------------------------------------------------------------------
# HMAC-SHA-256 token signing
# ---------------------------------------------------------------------------


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA-256 of ``payload_bytes`` using ``secret``.

    Args:
        payload_bytes: Raw bytes to sign.
        secret: ASCII secret string (treated as UTF-8).

    Returns:
        64-character lowercase hex digest.
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    """Constant-time verification of an HMAC-SHA-256 signature.

    Args:
        payload_bytes: The signed payload bytes.
        signature: Hex digest to verify against.
        secret: The signing secret.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.
    """
    expected = sign_payload(payload_bytes, secret)
    return hmac.compare_digest(expected, signature)


def sha256_hex(data: str) -> str:
    """Return the SHA-256 hex digest of a UTF-8 string (used for token hashing)."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
