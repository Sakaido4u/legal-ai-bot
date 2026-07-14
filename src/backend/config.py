from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMPLIANCE_", env_file=".env", extra="ignore")

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    index_dir: str | None = "vector_store/regulatory"
    use_demo_index: bool = False
    min_retrieval_score: float = 0.22
    retrieval_top_k: int = 6
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # LLM: template | openai | ollama
    llm_provider: str = "ollama"
    llm_model: str = "compliance-llm"
    llm_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    ollama_base_url: str = "http://127.0.0.1:11434"
    llm_timeout_seconds: float = 60.0

    # PostgreSQL
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/legal_ai"
    upload_dir: str = "data/uploads"
