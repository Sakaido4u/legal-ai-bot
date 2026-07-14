"""Helpers to turn RAG risk_scores into history-friendly summary fields.

compliance_score = round((1 - peak_risk) * 100)
risk_level       = highest level among risk_scores

This is the canonical backend scorer used by analyze responses and history.
"""

from __future__ import annotations

from typing import Any


_LEVEL_RANK = {"low": 1, "medium": 2, "high": 3}


def derived_compliance_score(risk_scores: list[dict[str, Any]]) -> int:
    if not risk_scores:
        return 100
    peak = max(float(r.get("score") or 0.0) for r in risk_scores)
    peak = min(1.0, max(0.0, peak))
    return int(round((1.0 - peak) * 100))


def derived_risk_level(risk_scores: list[dict[str, Any]]) -> str:
    if not risk_scores:
        return "low"
    best = "low"
    best_rank = 0
    for row in risk_scores:
        level = str(row.get("level") or "low").lower()
        rank = _LEVEL_RANK.get(level, 0)
        if rank > best_rank:
            best_rank = rank
            best = level if level in _LEVEL_RANK else "low"
    return best


def summarize_jurisdictions(jurisdictions: list[str]) -> str:
    if not jurisdictions:
        return "UNKNOWN"
    # Prefer a single primary code for FE tables; keep multi as comma-joined.
    if len(jurisdictions) == 1:
        return jurisdictions[0]
    return ",".join(jurisdictions)
