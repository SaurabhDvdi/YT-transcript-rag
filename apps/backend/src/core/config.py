"""Application configuration and environment settings."""

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class Settings:
    environment: str = "development"
    api_version: str = "0.1.0"
    service_name: str = "youtube-ai-api"
    allowed_origins: str = (
        "chrome-extension://*,moz-extension://*,http://localhost:*,http://127.0.0.1:*"
    )
    gemini_api_key: str | None = None
    cf_account_id: str | None = None
    cf_api_token: str | None = None
    daily_question_quota: int = 30
    daily_transcript_quota: int = 20
    max_concurrent_streams: int = 1
    cache_ttl_video_status: int = 60
    cache_ttl_transcript: int = 86400
    cache_ttl_retrieval: int = 3600
    retention_usage_events_days: int = 30
    retention_jobs_days: int = 7
    stale_job_timeout_seconds: int = 120
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: int = 30
    admin_api_key: str = "yt-ai-admin-secret"
    # Auth
    auth_token_secret: str = "dev-insecure-secret-change-in-prod-32chars"
    access_token_ttl_seconds: int = 900  # 15 minutes
    refresh_token_ttl_days: int = 30

    @property
    def ALLOWED_ORIGINS(self) -> str:
        return self.allowed_origins

    @property
    def SERVICE_NAME(self) -> str:
        return self.service_name

    @property
    def API_VERSION(self) -> str:
        return self.api_version

    @classmethod
    def from_env(cls, env: Any = None) -> "Settings":
        """Load settings from Cloudflare Worker env object or os.environ."""

        def get_val(key: str, default: str = "") -> str:
            if env is not None and hasattr(env, key):
                return str(getattr(env, key))
            if env is not None and isinstance(env, dict) and key in env:
                return str(env[key])
            return os.getenv(key, default)

        def get_int(key: str, default: int) -> int:
            val = get_val(key, "")
            try:
                return int(val) if val else default
            except ValueError:
                return default

        return cls(
            environment=get_val("ENVIRONMENT", "development"),
            api_version=get_val("API_VERSION", "0.1.0"),
            service_name=get_val("SERVICE_NAME", "youtube-ai-api"),
            allowed_origins=get_val(
                "ALLOWED_ORIGINS",
                "chrome-extension://*,moz-extension://*,http://localhost:*,http://127.0.0.1:*",
            ),
            gemini_api_key=get_val("GEMINI_API_KEY") or None,
            cf_account_id=get_val("CF_ACCOUNT_ID") or None,
            cf_api_token=get_val("CF_API_TOKEN") or None,
            daily_question_quota=get_int("DAILY_QUESTION_QUOTA", 30),
            daily_transcript_quota=get_int("DAILY_TRANSCRIPT_QUOTA", 20),
            max_concurrent_streams=get_int("MAX_CONCURRENT_STREAMS", 1),
            cache_ttl_video_status=get_int("CACHE_TTL_VIDEO_STATUS", 60),
            cache_ttl_transcript=get_int("CACHE_TTL_TRANSCRIPT", 86400),
            cache_ttl_retrieval=get_int("CACHE_TTL_RETRIEVAL", 3600),
            retention_usage_events_days=get_int("RETENTION_USAGE_EVENTS_DAYS", 30),
            retention_jobs_days=get_int("RETENTION_JOBS_DAYS", 7),
            stale_job_timeout_seconds=get_int("STALE_JOB_TIMEOUT_SECONDS", 120),
            circuit_breaker_failure_threshold=get_int("CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3),
            circuit_breaker_cooldown_seconds=get_int("CIRCUIT_BREAKER_COOLDOWN_SECONDS", 30),
            admin_api_key=get_val("ADMIN_API_KEY", "yt-ai-admin-secret"),
            auth_token_secret=get_val(
                "AUTH_TOKEN_SECRET", "dev-insecure-secret-change-in-prod-32chars"
            ),
            access_token_ttl_seconds=get_int("ACCESS_TOKEN_TTL_SECONDS", 900),
            refresh_token_ttl_days=get_int("REFRESH_TOKEN_TTL_DAYS", 30),
        )


DEV_AUTH_SECRET = "dev-insecure-secret-change-in-prod-32chars"
DEV_ADMIN_KEY = "yt-ai-admin-secret"


def validate_production_settings(s: Settings) -> list[str]:
    """Validate settings for production release readiness.

    Returns a list of security issues (empty if configuration is valid for production).
    """
    issues: list[str] = []

    # 1. Auth secret validation
    if not s.auth_token_secret or s.auth_token_secret == DEV_AUTH_SECRET:
        issues.append("AUTH_TOKEN_SECRET cannot be the default development secret in production.")
    elif len(s.auth_token_secret) < 32:
        issues.append("AUTH_TOKEN_SECRET must be at least 32 characters long.")

    # 2. Admin key validation
    if not s.admin_api_key or s.admin_api_key == DEV_ADMIN_KEY:
        issues.append("ADMIN_API_KEY cannot be the default development secret in production.")
    elif len(s.admin_api_key) < 16:
        issues.append("ADMIN_API_KEY must be at least 16 characters long.")

    # 3. Allowed origins validation
    origins = [o.strip() for o in s.allowed_origins.split(",") if o.strip()]
    for origin in origins:
        if origin == "*":
            issues.append("Wildcard '*' in ALLOWED_ORIGINS is prohibited in production.")
        if "localhost" in origin or "127.0.0.1" in origin:
            issues.append(
                f"Local development origin '{origin}' in ALLOWED_ORIGINS is prohibited in production."
            )

    # 4. AI Provider keys
    if not s.gemini_api_key and not (s.cf_account_id and s.cf_api_token):
        issues.append(
            "At least one AI provider (GEMINI_API_KEY or CF_ACCOUNT_ID + CF_API_TOKEN) must be configured."
        )

    return issues


_cached_settings: Settings | None = None


def get_settings(env: Any = None) -> Settings:
    global _cached_settings
    if env is not None:
        return Settings.from_env(env)
    if _cached_settings is None:
        _cached_settings = Settings.from_env()
    return _cached_settings


settings = get_settings()
