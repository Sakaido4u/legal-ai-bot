"""Login -> query -> results -> PDF demo: one analysis run, persisted for reload.

Reuses ``run_legal_query`` (retrieval, risk scoring, LLM answer and the
``analysis_logs`` row) and the batch relevance threshold, then stores the run in
``compliance_analyses`` so the results page and PDF have a stable id. The stored
JSON keeps the ``/v1/compliance/analyze`` shape so the React history can open
demo runs too; demo-only fields live under ``meta["demo"]``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.analysis_summary import derived_risk_level, summarize_jurisdictions
from backend.rag_service import RAGEngine
from database import crud
from ml.schemas import Jurisdiction
from services.batch_service import DEFAULT_THRESHOLD, flatten_query_result
from services.query_service import run_legal_query

REGULATION_CHOICES: dict[str, list[Jurisdiction]] = {
    "ALL": list(Jurisdiction),
    "GDPR": [Jurisdiction.GDPR],
    "DPDP": [Jurisdiction.DPDP],
    "CCPA": [Jurisdiction.CCPA],
}
REFUSAL_TEXT = (
    "No answer was generated: the retrieved passages did not support a fully cited answer. "
    "Review the cited sources below."
)
PRODUCT_FEATURE = "General compliance review"


def _short(text: str | None, limit: int = 80) -> str | None:
    """Section headings are sometimes whole sentences; keep labels to one line."""
    if not text:
        return text
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def overall_risk(hits: list[dict]) -> tuple[int, str]:
    """Peak passage risk as 0-100 plus its level — the same rule as risk_service."""
    rows = [{"score": h["risk_score"] or 0.0, "level": h["risk_level"] or "low"} for h in hits]
    peak = max((r["score"] for r in rows), default=0.0)
    return int(round(min(1.0, max(0.0, peak)) * 100)), derived_risk_level(rows)


def run_demo_query(
    db: Session,
    engine: RAGEngine,
    *,
    question: str,
    regulation: str,
    username: str,
    threshold: float = DEFAULT_THRESHOLD,
) -> int:
    """Run one analysis, persist it, and return its compliance_analyses id."""
    jurisdictions = REGULATION_CHOICES[regulation]
    result = run_legal_query(
        db,
        engine,
        question=question,
        product_feature=PRODUCT_FEATURE,
        jurisdictions=jurisdictions,
    )

    rows = flatten_query_result(result, threshold=threshold)
    hits = [r for r in rows if r["above_threshold"]]
    risk_score, risk_level = overall_risk(hits)
    answer = (result.get("answer") or "").strip()

    demo = {
        "username": username,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "regulation": regulation,
        "threshold": threshold,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "answer": answer or REFUSAL_TEXT,
        "answer_refused": not answer,
        "retrieved_count": len(rows),
        "citations": [
            {
                "citation_id": h["citation_id"],
                "jurisdiction": h["jurisdiction"],
                "section": _short(h["section"]),
                # source_label is "<document> | <heading>"; the heading is shown separately.
                "document": (h["document"] or "").split(" | ", 1)[0],
                "score": h["score"],
                "excerpt": h["excerpt"],
            }
            for h in hits
        ],
    }
    payload: dict[str, Any] = {
        "query": question,
        "product_feature": PRODUCT_FEATURE,
        "citations": result.get("citations", []),
        "risk_scores": result.get("risk_scores", []),
        "risk_heatmap": [
            {
                "citation_id": r["citation_id"],
                "chunk_id": r["chunk_id"],
                "jurisdiction": r["jurisdiction"],
                "risk_level": r["risk_level"],
                "risk_score": r["risk_score"],
                "factors": [],
            }
            for r in rows
        ],
        "cross_jurisdiction": result.get("cross_jurisdiction") or {"by_jurisdiction": {}},
        "llm": {
            "answer_text": answer,
            "citation_ids_used": result.get("citation_ids_used", []),
            "refused_insufficient_citations": not answer,
        },
        "compliance_score": 100 - risk_score,
        "risk_level": risk_level,
        "meta": {**result.get("meta", {}), "score_method": "100 - peak_risk*100", "demo": demo},
    }

    row = crud.create_compliance_analysis(
        db,
        query=question,
        jurisdiction=summarize_jurisdictions([j.value for j in jurisdictions]),
        compliance_score=100 - risk_score,
        risk_level=risk_level,
        result_json=json.dumps(payload, default=str),
    )
    db.commit()
    return row.id


def load_demo_result(db: Session, analysis_id: int) -> dict | None:
    """The stored demo view of a run, or None if missing / not a demo run."""
    row = crud.get_compliance_analysis(db, analysis_id)
    if row is None or not row.result_json:
        return None
    try:
        payload = json.loads(row.result_json)
    except json.JSONDecodeError:
        return None
    demo = (payload.get("meta") or {}).get("demo")
    if not demo:
        return None
    return {"id": row.id, "query": payload.get("query", row.query), **demo}
