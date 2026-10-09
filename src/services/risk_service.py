from __future__ import annotations

import logging
import time

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from database import crud
from ml.llm_citations import passages_to_citations
from ml.risk_scorer import score_passage
from ml.schemas import Jurisdiction, RetrievedPassage

if TYPE_CHECKING:
    from backend.rag_service import RAGEngine

logger = logging.getLogger(__name__)


def _filter_passages_by_document(
    passages: list[RetrievedPassage],
    allowed_refs: set[str],
) -> list[RetrievedPassage]:
    if not allowed_refs:
        return passages
    return [p for p in passages if any(ref.endswith(p.chunk_id) for ref in allowed_refs)]


def run_risk_analysis(
    db: Session,
    engine: RAGEngine,
    *,
    query: str,
    product_feature: str,
    jurisdictions: list[Jurisdiction],
    document_id: int | None = None,
    top_k: int | None = None,
) -> dict:
    """
    Retrieve passages and score compliance risk without invoking the LLM.
    """
    start = time.perf_counter()

    allowed_refs: set[str] = set()
    if document_id is not None:
        allowed_refs = crud.get_chunk_vector_references_for_document(db, document_id)

    k = top_k or engine.settings.retrieval_top_k
    passages = engine.retriever.retrieve(query, jurisdictions, top_k=k, use_mmr=True)

    if allowed_refs:
        passages = _filter_passages_by_document(passages, allowed_refs)

    citations = passages_to_citations(passages)
    risk_scores = [score_passage(p) for p in passages]

    heatmap_rows: list[dict] = []
    for i, rs in enumerate(risk_scores):
        heatmap_rows.append(
            {
                "citation_id": f"C{i}",
                "chunk_id": rs.chunk_id,
                "jurisdiction": rs.jurisdiction.value,
                "risk_level": rs.level.value,
                "risk_score": round(rs.score, 4),
                "factors": rs.factors,
            }
        )

    elapsed = time.perf_counter() - start

    overall_score = max((rs.score for rs in risk_scores), default=0.0)
    overall_level = "low"
    if overall_score >= 0.55:
        overall_level = "high"
    elif overall_score >= 0.28:
        overall_level = "medium"

    return {
        "query": query,
        "product_feature": product_feature,
        "overall_risk_level": overall_level,
        "overall_risk_score": round(overall_score, 4),
        "risk_scores": [r.model_dump() for r in risk_scores],
        "risk_heatmap": heatmap_rows,
        "citations": [c.model_dump() for c in citations],
        "response_time": round(elapsed, 4),
        "meta": {
            "document_id": document_id,
            "passages_analyzed": len(passages),
            "retrieval_min_score": engine.settings.min_retrieval_score,
        },
    }
