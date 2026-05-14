from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMPLIANCE_", env_file=".env", extra="ignore")

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    index_dir: str | None = None
    use_demo_index: bool = True
    min_retrieval_score: float = 0.22
    retrieval_top_k: int = 6
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
