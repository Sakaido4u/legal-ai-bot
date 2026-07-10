from __future__ import annotations

from fastapi import HTTPException

from backend.config import Settings
from backend.rag_service import RAGEngine

_engine: RAGEngine | None = None


def set_engine(engine: RAGEngine | None) -> None:
    global _engine
    _engine = engine


def get_engine() -> RAGEngine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return _engine


def get_settings() -> Settings:
    return Settings()
