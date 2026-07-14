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
from ml.schemas import Citation, CrossJurisdictionResult, Jurisdiction, LLMComplianceAnswer, RiskScore
from ml.vector_store import ComplianceVectorStore

from .config import Settings


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
) -> dict:
    k = top_k or engine.settings.retrieval_top_k
    passages = engine.retriever.retrieve(
        query,
        jurisdictions,
        top_k=k,
        use_mmr=True,
    )
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

    return {
        "query": query,
        "product_feature": product_feature,
        "citations": [c.model_dump() for c in citations],
        "risk_scores": [r.model_dump() for r in risk_scores],
        "risk_heatmap": heatmap_rows,
        "cross_jurisdiction": cross.model_dump(),
        "llm": llm.model_dump(),
        "meta": {
            "index_total_vectors": engine.store.ntotal(),
            "retrieval_min_score": engine.settings.min_retrieval_score,
        },
    }
