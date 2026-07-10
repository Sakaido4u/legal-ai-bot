from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database.session import init_db
from ml.ollama_health import check_ollama_llm
from ml.schemas import Jurisdiction

from .config import Settings
from .deps import get_engine, set_engine
from .middleware import RequestLoggingMiddleware
from .rag_service import RAGEngine, build_engine, run_compliance_analysis
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

_boot_settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    init_db()
    engine = build_engine(settings)
    set_engine(engine)
    logger.info("RAG engine ready (index vectors=%s)", engine.store.ntotal())
    if settings.llm_provider == "ollama":
        ollama = check_ollama_llm(settings.ollama_base_url, settings.llm_model)
        if ollama["status"] != "ok":
            logger.warning("Ollama LLM degraded: %s", ollama)
        else:
            logger.info("Ollama LLM ready: model=%s", settings.llm_model)
    yield
    set_engine(None)


app = FastAPI(
    title="Legal AI Compliance Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _boot_settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=4000)
    product_feature: str = Field(..., min_length=2, max_length=2000)
    jurisdictions: list[str] = Field(
        default_factory=lambda: [Jurisdiction.GDPR.value, Jurisdiction.DPDP.value, Jurisdiction.CCPA.value]
    )
    top_k: int | None = Field(default=None, ge=1, le=24)


@app.get("/")
async def root():
    return {
        "service": "Legal AI Compliance Assistant",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "upload": "POST /documents/upload",
            "documents": "GET /documents",
            "legal_query": "POST /legal_query",
            "risk_analysis": "POST /risk_analysis",
            "legacy_analyze": "POST /v1/compliance/analyze",
        },
    }


@app.get("/health")
async def health():
    try:
        engine = get_engine()
    except HTTPException:
        return {"status": "starting", "index_vectors": 0, "embedding_model": None}

    payload = {
        "status": "ok",
        "index_vectors": engine.store.ntotal(),
        "embedding_model": engine.settings.embedding_model,
        "llm_provider": engine.settings.llm_provider,
        "llm_model": engine.settings.llm_model,
    }
    if engine.settings.llm_provider == "ollama":
        payload["ollama"] = check_ollama_llm(
            engine.settings.ollama_base_url,
            engine.settings.llm_model,
        )
        if payload["ollama"]["status"] != "ok":
            payload["status"] = "degraded"
    return payload


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
