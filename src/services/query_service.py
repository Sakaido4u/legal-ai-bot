from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from backend.rag_service import RAGEngine
from database import crud
from ml.cross_jurisdiction import compare_cross_jurisdiction
from ml.llm_backend import generate_with_llm
from ml.llm_citations import passages_to_citations, validate_citation_coverage
from ml.risk_scorer import score_passage
from ml.schemas import Jurisdiction, LLMComplianceAnswer, RetrievedPassage

logger = logging.getLogger(__name__)


def _filter_passages_by_document(
    passages: list[RetrievedPassage],
    allowed_refs: set[str],
) -> list[RetrievedPassage]:
    if not allowed_refs:
        return passages
    return [p for p in passages if any(ref.endswith(p.chunk_id) for ref in allowed_refs)]


def run_legal_query(
    db: Session,
    engine: RAGEngine,
    *,
    question: str,
    product_feature: str,
    jurisdictions: list[Jurisdiction],
    document_id: int | None = None,
    top_k: int | None = None,
) -> dict:
    """Retrieve relevant chunks, run RAG compliance analysis, log evaluation metadata."""
    start = time.perf_counter()

    allowed_refs: set[str] = set()
    if document_id is not None:
        allowed_refs = crud.get_chunk_vector_references_for_document(db, document_id)

    k = top_k or engine.settings.retrieval_top_k
    passages = engine.retriever.retrieve(question, jurisdictions, top_k=k, use_mmr=True)
    passages = _filter_passages_by_document(passages, allowed_refs)

    if not passages:
        elapsed = time.perf_counter() - start
        crud.create_analysis_log(
            db,
            question=question,
            response_time=elapsed,
            document_id=document_id,
        )
        db.commit()
        return {
            "question": question,
            "answer": "",
            "citations": [],
            "refused_insufficient_citations": True,
            "response_time": round(elapsed, 4),
            "meta": {"document_id": document_id, "passages_found": 0},
        }

    citations = passages_to_citations(passages)
    risk_scores = [score_passage(p) for p in passages]
    cross = compare_cross_jurisdiction(passages, jurisdictions=jurisdictions)
    llm: LLMComplianceAnswer = generate_with_llm(
        query=question,
        product_feature=product_feature,
        citations=citations,
        provider=engine.settings.llm_provider,  # type: ignore[arg-type]
        model=engine.settings.llm_model,
        api_key=engine.settings.llm_api_key,
        openai_base_url=engine.settings.openai_base_url,
        ollama_base_url=engine.settings.ollama_base_url,
        timeout=engine.settings.llm_timeout_seconds,
    )
    if llm.answer_text and not validate_citation_coverage(
        llm.answer_text, [c.citation_id for c in citations]
    ):
        llm = LLMComplianceAnswer(
            answer_text="",
            citation_ids_used=[],
            refused_insufficient_citations=True,
        )

    elapsed = time.perf_counter() - start
    crud.create_analysis_log(
        db,
        question=question,
        response_time=elapsed,
        document_id=document_id,
    )
    db.commit()

    return {
        "question": question,
        "answer": llm.answer_text,
        "citations": [c.model_dump() for c in citations],
        "risk_scores": [r.model_dump() for r in risk_scores],
        "cross_jurisdiction": cross.model_dump(),
        "refused_insufficient_citations": llm.refused_insufficient_citations,
        "citation_ids_used": llm.citation_ids_used,
        "response_time": round(elapsed, 4),
        "meta": {
            "document_id": document_id,
            "passages_found": len(passages),
            "index_total_vectors": engine.store.ntotal(),
        },
    }
