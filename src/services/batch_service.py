"""Batch querying on top of ``run_legal_query`` with a relevance threshold.

Score semantics
---------------
The retriever returns ``similarity`` = inner product of L2-normalized
embeddings (FAISS ``IndexFlatIP``), i.e. cosine similarity in [-1, 1], higher is
better. It is NOT a distance. Before thresholding we map it to [0, 1]:

* ``clip``  (default): ``min(1, max(0, cos))`` — negative cosine (unrelated)
  becomes 0, positive values are kept as-is, so a 0.5 threshold means
  cosine >= 0.5.
* ``shift``: ``(cos + 1) / 2`` — linear rescale; a 0.5 threshold here means
  cosine >= 0, which keeps almost every retrieved chunk.

A passage is a *hit* when its normalized score is strictly above the threshold.
"""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy.orm import Session

from backend.rag_service import RAGEngine
from ml.schemas import Jurisdiction
from services.query_service import run_legal_query

logger = logging.getLogger(__name__)

ScoreMode = Literal["clip", "shift"]
SCORE_MODES: tuple[str, ...] = ("clip", "shift")
DEFAULT_THRESHOLD = 0.5
SNIPPET_CHARS = 300


def normalize_similarity(cosine: float, mode: ScoreMode = "clip") -> float:
    """Map a cosine similarity in [-1, 1] to a 0–1 relevance score."""
    if mode == "clip":
        return min(1.0, max(0.0, cosine))
    if mode == "shift":
        return min(1.0, max(0.0, (cosine + 1.0) / 2.0))
    raise ValueError(f"Unknown score mode {mode!r}; expected one of {SCORE_MODES}")


def _snippet(text: str | None, limit: int = SNIPPET_CHARS) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def flatten_query_result(
    result: dict,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    score_mode: ScoreMode = "clip",
) -> list[dict]:
    """
    One row per retrieved citation of a ``run_legal_query`` result.

    ``citations`` and ``risk_scores`` are built from the same passage list in the
    same order, so they are joined by position.
    """
    citations = result.get("citations") or []
    risks = result.get("risk_scores") or []
    answer = _snippet(result.get("answer"))

    rows: list[dict] = []
    for rank, cit in enumerate(citations, start=1):
        risk = risks[rank - 1] if rank - 1 < len(risks) else {}
        cosine = float(cit.get("similarity", 0.0))
        score = normalize_similarity(cosine, score_mode)
        level = risk.get("level")
        rows.append(
            {
                "query": result.get("question", ""),
                "rank": rank,
                "citation_id": cit.get("citation_id"),
                "chunk_id": risk.get("chunk_id"),
                "section": cit.get("heading"),
                "document": cit.get("source_label"),
                "jurisdiction": str(getattr(cit.get("jurisdiction"), "value", cit.get("jurisdiction"))),
                "cosine": round(cosine, 4),
                "score": round(score, 4),
                "above_threshold": score > threshold,
                "risk_level": str(getattr(level, "value", level)) if level is not None else None,
                "risk_score": round(float(risk["score"]), 4) if "score" in risk else None,
                "excerpt": _snippet(cit.get("excerpt")),
                "answer_snippet": answer,
            }
        )
    return rows


def summarize_query(query: str, rows: list[dict], result: dict | None, error: str | None) -> dict:
    hits = [r for r in rows if r["above_threshold"]]
    scores = [r["score"] for r in hits]
    return {
        "query": query,
        "answer": (result or {}).get("answer", ""),
        "retrieved_count": len(rows),
        "hit_count": len(hits),
        "top_score": max(scores) if scores else None,
        "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
        "response_time": (result or {}).get("response_time"),
        "error": error,
        "hits": hits,
        # All retrieved rows (hits and non-hits) — used for score histograms.
        "retrieved": rows,
    }


def run_batch_queries(
    db: Session,
    engine: RAGEngine,
    queries: list[str],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    score_mode: ScoreMode = "clip",
    product_feature: str = "General compliance review",
    jurisdictions: list[Jurisdiction] | None = None,
    document_id: int | None = None,
    top_k: int | None = None,
    on_progress=None,
) -> list[dict]:
    """
    Run each query through ``run_legal_query`` and apply the relevance threshold.

    A failure on one query is recorded in its ``error`` field and the batch
    continues with the next query.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    normalize_similarity(0.0, score_mode)  # validate mode early
    js = jurisdictions or list(Jurisdiction)

    summaries: list[dict] = []
    for i, query in enumerate(queries, start=1):
        result: dict | None = None
        error: str | None = None
        try:
            result = run_legal_query(
                db,
                engine,
                question=query,
                product_feature=product_feature,
                jurisdictions=js,
                document_id=document_id,
                top_k=top_k,
            )
            rows = flatten_query_result(result, threshold=threshold, score_mode=score_mode)
        except Exception as exc:  # keep the batch going
            logger.exception("batch_query_failure query=%r", query)
            db.rollback()
            error = f"{type(exc).__name__}: {exc}"
            rows = []
        summary = summarize_query(query, rows, result, error)
        summaries.append(summary)
        if on_progress is not None:
            on_progress(i, len(queries), summary)
    return summaries
