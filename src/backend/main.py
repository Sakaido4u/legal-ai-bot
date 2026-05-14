from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.schemas import Jurisdiction

from .config import Settings
from .rag_service import RAGEngine, build_engine, run_compliance_analysis

logger = logging.getLogger(__name__)

_engine: RAGEngine | None = None
_boot_settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    settings = Settings()
    _engine = build_engine(settings)
    logger.info("RAG engine ready (index vectors=%s)", _engine.store.ntotal())
    yield
    _engine = None


app = FastAPI(
    title="Cross-Jurisdictional Product Compliance RAG",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _boot_settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_engine() -> RAGEngine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return _engine


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=4000)
    product_feature: str = Field(..., min_length=2, max_length=2000)
    jurisdictions: list[str] = Field(
        default_factory=lambda: [Jurisdiction.GDPR.value, Jurisdiction.DPDP.value, Jurisdiction.CCPA.value]
    )
    top_k: int | None = Field(default=None, ge=1, le=24)


@app.get("/health")
async def health():
    if _engine is None:
        return {"status": "starting", "index_vectors": 0, "embedding_model": None}
    return {
        "status": "ok",
        "index_vectors": _engine.store.ntotal(),
        "embedding_model": _engine.settings.embedding_model,
    }


@app.post("/v1/compliance/analyze")
async def compliance_analyze(
    body: AnalyzeRequest,
    engine: Annotated[RAGEngine, Depends(get_engine)],
):
    try:
        js = [Jurisdiction(j) for j in body.jurisdictions]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid jurisdiction: {e}") from e

    if engine.store.is_empty():
        raise HTTPException(
            status_code=503,
            detail="Vector index is empty. Ingest documents or set COMPLIANCE_USE_DEMO_INDEX=true.",
        )

    return await asyncio.to_thread(
        run_compliance_analysis,
        engine,
        query=body.query,
        product_feature=body.product_feature,
        jurisdictions=js,
        top_k=body.top_k,
    )


@app.get("/v1/compliance/jurisdictions")
async def list_jurisdictions():
    return {"jurisdictions": [j.value for j in Jurisdiction]}
