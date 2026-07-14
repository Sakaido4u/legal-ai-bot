from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.config import Settings

# Avoid importing rag_service here — it pulls torch/FAISS and can hard-crash
# on some Windows + Python builds at import time.
_engine: Any | None = None


def set_engine(engine: Any | None) -> None:
    global _engine
    _engine = engine


def get_engine() -> Any:
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail="RAG engine not initialized (ML stack failed to load, or still starting).",
        )
    return _engine


def get_settings() -> Settings:
    return Settings()
