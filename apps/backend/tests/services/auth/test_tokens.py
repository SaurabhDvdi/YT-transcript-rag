"""Tests for auth token creation and decoding."""

import time

from src.services.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_refresh_token,
)

SECRET = "test-secret-12345678901234567890ab"
USER_ID = "test-user-uuid-1234"
EMAIL = "user@example.com"


class TestAccessToken:
    def test_create_and_decode(self) -> None:
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=300)
        claims = decode_access_token(token, SECRET)
        assert claims is not None
        assert claims.user_id == USER_ID
        assert claims.email == EMAIL

    def test_wrong_secret_returns_none(self) -> None:
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=300)
        assert decode_access_token(token, "wrong-secret") is None

    def test_expired_token_returns_none(self) -> None:
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=-1)
        assert decode_access_token(token, SECRET) is None

    def test_tampered_payload_returns_none(self) -> None:
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=300)
        # Flip a character in the payload (before the ".")
        parts = token.split(".")
        tampered_payload = parts[0][:-1] + ("X" if parts[0][-1] != "X" else "Y")
        tampered_token = f"{tampered_payload}.{parts[1]}"
        assert decode_access_token(tampered_token, SECRET) is None

    def test_malformed_token_returns_none(self) -> None:
        assert decode_access_token("not.a.valid.token", SECRET) is None
        assert decode_access_token("", SECRET) is None
        assert decode_access_token("no-dot", SECRET) is None

    def test_claims_expiry_is_in_future(self) -> None:
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=900)
        claims = decode_access_token(token, SECRET)
        assert claims is not None
        assert claims.expires_at > int(time.time())

    def test_issued_at_is_recent(self) -> None:
        before = int(time.time())
        token = create_access_token(USER_ID, EMAIL, SECRET, ttl_seconds=900)
        after = int(time.time())
        claims = decode_access_token(token, SECRET)
        assert claims is not None
        assert before <= claims.issued_at <= after


class TestRefreshToken:
    def test_creates_raw_and_hash(self) -> None:
        raw, token_hash = create_refresh_token()
        assert isinstance(raw, str)
        assert len(raw) == 64  # 32 hex bytes
        assert isinstance(token_hash, str)
        assert len(token_hash) == 64

    def test_hash_is_deterministic(self) -> None:
        raw, _ = create_refresh_token()
        h1 = hash_refresh_token(raw)
        h2 = hash_refresh_token(raw)
        assert h1 == h2

    def test_different_tokens_different_hashes(self) -> None:
        raw1, hash1 = create_refresh_token()
        raw2, hash2 = create_refresh_token()
        assert raw1 != raw2
        assert hash1 != hash2

    def test_create_refresh_token_stored_hash_matches(self) -> None:
        raw, stored_hash = create_refresh_token()
        assert hash_refresh_token(raw) == stored_hash
