from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ml.cross_jurisdiction import compare_cross_jurisdiction
from ml.demo_corpus import demo_chunks
from ml.embeddings import EmbeddingBackend
from ml.llm_backend import generate_with_llm, resolve_llm_provider
from ml.llm_citations import passages_to_citations, validate_citation_answer
from ml.retriever import HighPrecisionRetriever
from ml.risk_scorer import score_passage
from backend.analysis_summary import derived_compliance_score, derived_risk_level
from ml.schemas import Citation, CrossJurisdictionResult, Jurisdiction, LLMComplianceAnswer, RetrievedPassage, RiskScore
from ml.vector_store import ComplianceVectorStore

from .config import Settings


def _filter_passages_by_document(
    passages: list[RetrievedPassage],
    allowed_refs: set[str],
) -> list[RetrievedPassage]:
    """Keep passages whose chunk_id appears in the document's vector_reference set."""
    if not allowed_refs:
        return []
    return [p for p in passages if any(ref.endswith(p.chunk_id) for ref in allowed_refs)]


@dataclass
class RAGEngine:
    settings: Settings
    embedder: EmbeddingBackend
    store: ComplianceVectorStore
    retriever: HighPrecisionRetriever


def build_engine(settings: Settings) -> RAGEngine:
    embedder = EmbeddingBackend(settings.embedding_model)
    store: ComplianceVectorStore | None = None

    if settings.index_dir:
        p = Path(settings.index_dir)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p
        if (p / "manifest.json").is_file():
            store = ComplianceVectorStore.load(p)

    if store is None:
        store = ComplianceVectorStore(embedder.dim)

    if store.is_empty() and settings.use_demo_index:
        chunks = demo_chunks()
        embs = embedder.encode([c.text for c in chunks])
        store.add(embs, chunks)

    retriever = HighPrecisionRetriever(
        store,
        embedder,
        min_score=settings.min_retrieval_score,
    )
    return RAGEngine(settings=settings, embedder=embedder, store=store, retriever=retriever)


def run_compliance_analysis(
    engine: RAGEngine,
    *,
    query: str,
    product_feature: str,
    jurisdictions: list[Jurisdiction],
    top_k: int | None = None,
    document_id: int | None = None,
    allowed_chunk_refs: set[str] | None = None,
) -> dict:
    """
    Run RAG compliance analysis.

    When ``allowed_chunk_refs`` is provided (from an uploaded ``document_id``),
    passages are filtered to that document's indexed chunks so the answer is
    grounded in the uploaded PDF — same pattern as ``/legal_query``.
    """
    k = top_k or engine.settings.retrieval_top_k
    # Pull a wider candidate set when scoping to a document, then filter.
    retrieve_k = k * 4 if allowed_chunk_refs is not None else k
    passages = engine.retriever.retrieve(
        query,
        jurisdictions,
        top_k=retrieve_k,
        use_mmr=True,
    )
    if allowed_chunk_refs is not None:
        passages = _filter_passages_by_document(passages, allowed_chunk_refs)[:k]

    citations: list[Citation] = passages_to_citations(passages)
    risk_scores = [score_passage(p) for p in passages]
    cross = compare_cross_jurisdiction(passages, jurisdictions=jurisdictions)
    llm_provider = resolve_llm_provider(
        engine.settings.llm_provider,
        ollama_base_url=engine.settings.ollama_base_url,
        llm_model=engine.settings.llm_model,
    )
    llm: LLMComplianceAnswer = generate_with_llm(
        query=query,
        product_feature=product_feature,
        citations=citations,
        provider=llm_provider,
        model=engine.settings.llm_model,
        api_key=engine.settings.llm_api_key,
        openai_base_url=engine.settings.openai_base_url,
        ollama_base_url=engine.settings.ollama_base_url,
        timeout=engine.settings.llm_timeout_seconds,
    )
    if llm.answer_text and not validate_citation_answer(
        llm.answer_text, [c.citation_id for c in citations], require_per_sentence=True
    ):
        llm = LLMComplianceAnswer(
            answer_text="",
            citation_ids_used=[],
            refused_insufficient_citations=True,
        )

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

    risk_dicts = [r.model_dump(mode="json") for r in risk_scores]
    compliance_score = derived_compliance_score(risk_dicts)
    risk_level = derived_risk_level(risk_dicts)

    return {
        "query": query,
        "product_feature": product_feature,
        "citations": [c.model_dump(mode="json") for c in citations],
        "risk_scores": risk_dicts,
        "risk_heatmap": heatmap_rows,
        "cross_jurisdiction": cross.model_dump(mode="json"),
        "llm": llm.model_dump(mode="json"),
        "compliance_score": compliance_score,
        "risk_level": risk_level,
        "meta": {
            "index_total_vectors": engine.store.ntotal(),
            "retrieval_min_score": engine.settings.min_retrieval_score,
            "document_id": document_id,
            "document_scoped": allowed_chunk_refs is not None,
            "passages_found": len(passages),
            "score_method": "100 - peak_risk*100",
        },
    }
