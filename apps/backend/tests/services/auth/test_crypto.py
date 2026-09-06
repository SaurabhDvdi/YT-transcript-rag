"""Tests for auth crypto primitives: PBKDF2 hashing and HMAC signing."""

from src.services.auth.crypto import (
    generate_salt,
    hash_password,
    sha256_hex,
    sign_payload,
    verify_password,
    verify_signature,
)


class TestGenerateSalt:
    def test_returns_hex_string(self) -> None:
        salt = generate_salt()
        assert isinstance(salt, str)
        assert len(salt) == 32  # 16 bytes → 32 hex chars
        int(salt, 16)  # should not raise

    def test_unique_on_each_call(self) -> None:
        salts = {generate_salt() for _ in range(100)}
        assert len(salts) == 100


class TestHashPassword:
    def test_produces_hex_string(self) -> None:
        salt = generate_salt()
        result = hash_password("password123", salt)
        assert isinstance(result, str)
        assert len(result) == 64  # 32-byte SHA-256 → 64 hex chars

    def test_same_inputs_same_output(self) -> None:
        salt = generate_salt()
        h1 = hash_password("mysecret", salt)
        h2 = hash_password("mysecret", salt)
        assert h1 == h2

    def test_different_passwords_different_hashes(self) -> None:
        salt = generate_salt()
        assert hash_password("password1", salt) != hash_password("password2", salt)

    def test_different_salts_different_hashes(self) -> None:
        h1 = hash_password("password", generate_salt())
        h2 = hash_password("password", generate_salt())
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password_accepted(self) -> None:
        salt = generate_salt()
        pw_hash = hash_password("correct-horse", salt)
        assert verify_password("correct-horse", salt, pw_hash) is True

    def test_wrong_password_rejected(self) -> None:
        salt = generate_salt()
        pw_hash = hash_password("correct-horse", salt)
        assert verify_password("wrong-horse", salt, pw_hash) is False

    def test_empty_password_rejected(self) -> None:
        salt = generate_salt()
        pw_hash = hash_password("actual-password", salt)
        assert verify_password("", salt, pw_hash) is False

    def test_wrong_salt_rejected(self) -> None:
        salt1 = generate_salt()
        salt2 = generate_salt()
        pw_hash = hash_password("password", salt1)
        assert verify_password("password", salt2, pw_hash) is False


class TestSignAndVerify:
    def test_signature_verifies(self) -> None:
        payload = b"hello world"
        secret = "my-secret-key"
        sig = sign_payload(payload, secret)
        assert verify_signature(payload, sig, secret) is True

    def test_tampered_payload_rejected(self) -> None:
        payload = b"hello world"
        secret = "my-secret-key"
        sig = sign_payload(payload, secret)
        assert verify_signature(b"hello world tampered", sig, secret) is False

    def test_wrong_secret_rejected(self) -> None:
        payload = b"hello world"
        sig = sign_payload(payload, "secret-a")
        assert verify_signature(payload, sig, "secret-b") is False

    def test_empty_payload(self) -> None:
        payload = b""
        secret = "sec"
        sig = sign_payload(payload, secret)
        assert verify_signature(payload, sig, secret) is True


class TestSha256Hex:
    def test_known_hash(self) -> None:
        # SHA-256 of empty string is well-known
        result = sha256_hex("")
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_non_empty(self) -> None:
        result = sha256_hex("hello")
        assert len(result) == 64
        assert isinstance(result, str)
