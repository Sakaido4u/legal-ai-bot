"""Shared test fixtures — SQLite + stubbed ML stack (no torch/FAISS)."""

from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import Generator
from unittest.mock import MagicMock

# ── Env before any Settings / session import ───────────────────
os.environ["COMPLIANCE_JWT_SECRET"] = "test-jwt-secret-0123456789abcdef0123456789ab"
os.environ["COMPLIANCE_APP_ENV"] = "development"
os.environ["COMPLIANCE_LLM_PROVIDER"] = "template"
os.environ["COMPLIANCE_USE_DEMO_INDEX"] = "true"
os.environ["COMPLIANCE_RATE_LIMIT_AUTH"] = "1000/minute"
os.environ["COMPLIANCE_RATE_LIMIT_UPLOAD"] = "1000/minute"
os.environ["COMPLIANCE_RATE_LIMIT_ANALYZE"] = "1000/minute"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

# ── Stub heavy optional deps so `import backend.main` is light ─
for name in ("torch", "faiss", "faiss_cpu", "sentence_transformers", "transformers", "datasets"):
    if name not in sys.modules:
        sys.modules[name] = MagicMock()


def _stub_module(fullname: str, **attrs) -> ModuleType:
    mod = ModuleType(fullname)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[fullname] = mod
    return mod


# Pre-stub ml leaves that pull torch at import time.
_stub_module(
    "ml.embeddings",
    EmbeddingBackend=MagicMock,
)
_stub_module(
    "ml.vector_store",
    ComplianceVectorStore=MagicMock,
)
_stub_module(
    "ml.retriever",
    HighPrecisionRetriever=MagicMock,
)
_stub_module(
    "ml.llm_backend",
    generate_with_llm=MagicMock(return_value="ok"),
    resolve_llm_provider=MagicMock(return_value="template"),
)
_stub_module("ml.demo_corpus", demo_chunks=MagicMock(return_value=[]))
_stub_module(
    "ml.cross_jurisdiction",
    compare_cross_jurisdiction=MagicMock(
        return_value={"by_jurisdiction": {}, "divergence_summary": "", "conflicts": []}
    ),
)
_stub_module(
    "ml.llm_citations",
    passages_to_citations=MagicMock(return_value=[]),
    validate_citation_answer=MagicMock(return_value=("ok", [], False)),
)
_stub_module("ml.risk_scorer", score_passage=MagicMock(return_value=None))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from database.base import Base  # noqa: E402
import database.models  # noqa: E402, F401
import database.session as db_session_mod  # noqa: E402
from database.session import get_db  # noqa: E402

_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_engine)
TestingSessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)

# Point the app's SessionLocal at the shared in-memory DB.
db_session_mod.engine = _engine
db_session_mod.SessionLocal = TestingSessionLocal


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    stub_engine = MagicMock()
    stub_engine.store.ntotal.return_value = 3
    stub_engine.store.is_empty.return_value = False
    stub_engine.settings.embedding_model = "test-embed"
    stub_engine.settings.llm_provider = "template"
    stub_engine.settings.llm_model = "template"
    stub_engine.settings.use_demo_index = True
    stub_engine.settings.ollama_base_url = "http://127.0.0.1:11434"

    monkeypatch.setattr("backend.main.build_engine", lambda _settings=None: stub_engine)
    monkeypatch.setattr(
        "backend.main.check_ollama_llm",
        lambda *a, **k: {"status": "skipped", "reachable": False, "model_available": False},
    )
    monkeypatch.setattr(
        "backend.main.run_compliance_analysis",
        lambda *a, **k: {
            "query": k.get("query", "q"),
            "product_feature": k.get("product_feature", "feature"),
            "citations": [],
            "risk_scores": [],
            "risk_heatmap": [],
            "cross_jurisdiction": {
                "by_jurisdiction": {},
                "divergence_summary": "",
                "conflicts": [],
            },
            "llm": {
                "answer_text": "stub",
                "citation_ids_used": [],
                "refused_insufficient_citations": False,
            },
            "compliance_score": 80,
            "risk_level": "low",
            "meta": {"score_method": "test"},
        },
    )

    from backend.main import app

    def _override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
