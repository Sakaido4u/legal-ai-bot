from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="COMPLIANCE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Allow DATABASE_URL (no prefix) via validation_alias below.
        populate_by_name=True,
    )

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    index_dir: str | None = "vector_store/regulatory"
    use_demo_index: bool = False
    min_retrieval_score: float = 0.22
    retrieval_top_k: int = 6
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # LLM: template | openai | ollama
    llm_provider: str = "ollama"
    llm_model: str = "compliance-llm"
    llm_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://127.0.0.1:11434"
    llm_timeout_seconds: float = 60.0

    # PostgreSQL — prefers DATABASE_URL, else COMPLIANCE_DATABASE_URL
    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/legal_ai",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "COMPLIANCE_DATABASE_URL",
            "database_url",
        ),
    )
    upload_dir: str = "data/uploads"

    # Auth / JWT — REQUIRED from env (COMPLIANCE_JWT_SECRET). No weak defaults.
    jwt_secret: str = Field(..., min_length=32)
    jwt_expire_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"

    # development | production — controls reset-token leak + email logging
    app_env: str = Field(
        default="development",
        validation_alias=AliasChoices("COMPLIANCE_APP_ENV", "APP_ENV", "ENV"),
    )

    # Rate limits (requests per window; window defaults to 60s)
    rate_limit_auth: str = "10/minute"
    rate_limit_upload: str = "20/minute"
    rate_limit_analyze: str = "30/minute"

    # SMTP password reset (optional — when unset, log-only delivery in development)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "noreply@lexai.local"
    smtp_use_tls: bool = True
    frontend_base_url: str = "http://localhost:3000"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        """Accept postgresql://… and pin the psycopg2 SQLAlchemy driver."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql+psycopg2://"):
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg2://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg2://" + value.removeprefix("postgresql://")
        return value

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def reject_placeholder_secret(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        weak = {
            "",
            "lexai-dev-secret-change-in-production",
            "change-me",
            "secret",
        }
        if value.strip() in weak:
            raise ValueError(
                "COMPLIANCE_JWT_SECRET is missing or weak. "
                "Generate one with: openssl rand -hex 32"
            )
        return value

    @model_validator(mode="after")
    def normalize_app_env(self) -> Settings:
        self.app_env = (self.app_env or "development").strip().lower()
        return self

    @property
    def is_development(self) -> bool:
        return self.app_env in {"development", "dev", "local", "test"}
