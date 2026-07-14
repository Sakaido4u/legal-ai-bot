from __future__ import annotations

from pydantic import AliasChoices, Field, field_validator
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

    # Auth / JWT (env: COMPLIANCE_JWT_SECRET, COMPLIANCE_JWT_EXPIRE_MINUTES)
    jwt_secret: str = "lexai-dev-secret-change-in-production"
    jwt_expire_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"

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
