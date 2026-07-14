"""Rate limiting via slowapi (env-configurable limits)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter
from slowapi.util import get_remote_address


class _RateLimitSettings(BaseSettings):
    """Separate from main Settings so JWT is not required at import time."""

    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    rate_limit_auth: str = "10/minute"
    rate_limit_upload: str = "20/minute"
    rate_limit_analyze: str = "30/minute"


_rl = _RateLimitSettings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
)

AUTH_LIMIT = _rl.rate_limit_auth
UPLOAD_LIMIT = _rl.rate_limit_upload
ANALYZE_LIMIT = _rl.rate_limit_analyze
