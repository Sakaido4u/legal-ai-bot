from __future__ import annotations

from collections import defaultdict

from .risk_scorer import score_passage
from .schemas import (
    ComplianceStance,
    CrossJurisdictionResult,
    Jurisdiction,
    JurisdictionComparison,
    RetrievedPassage,
    RiskLevel,
)


def _stance_for_passages(passages: list[RetrievedPassage]) -> tuple[ComplianceStance, float, list[str]]:
    """
    Map retrieved text to a coarse stance using risk scores + prohibition signals.
    confidence: heuristic in [0,1] based on hit strength and consistency.
    """
    if not passages:
        return ComplianceStance.UNCLEAR, 0.0, []

    risks = [score_passage(p) for p in passages]

    level_rank = {RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 1}
    worst = max(risks, key=lambda r: (level_rank[r.level], r.score))

    top_ids = [p.chunk_id for p in passages[:3]]

    if worst.level == RiskLevel.HIGH:
        return ComplianceStance.PROHIBITED, min(1.0, 0.55 + worst.score * 0.4), top_ids
    if worst.level == RiskLevel.MEDIUM:
        return ComplianceStance.RESTRICTED, min(1.0, 0.45 + worst.score * 0.35), top_ids
    return ComplianceStance.ALLOWED, min(1.0, 0.35 + max(r.score for r in risks) * 0.5), top_ids


def compare_cross_jurisdiction(
    passages: list[RetrievedPassage],
    *,
    jurisdictions: list[Jurisdiction],
) -> CrossJurisdictionResult:
    grouped: dict[Jurisdiction, list[RetrievedPassage]] = defaultdict(list)
    for p in passages:
        grouped[p.jurisdiction].append(p)

    by_j: dict[str, JurisdictionComparison] = {}
    for j in jurisdictions:
        pj = grouped.get(j, [])
        stance, conf, cids = _stance_for_passages(sorted(pj, key=lambda x: x.similarity, reverse=True))
        by_j[j.value] = JurisdictionComparison(
            jurisdiction=j,
            stance=stance,
            confidence=conf,
            top_citation_ids=cids,
        )

    pairs_flagged: list[dict[str, str]] = []
    # Flag meaningful divergences for product/legal review
    st = {j: by_j[j.value].stance for j in jurisdictions if j.value in by_j}
    for a in jurisdictions:
        for b in jurisdictions:
            if a >= b:
                continue
            sa, sb = st.get(a), st.get(b)
            if sa is None or sb is None:
                continue
            good = {ComplianceStance.ALLOWED, ComplianceStance.RESTRICTED}
            bad = {ComplianceStance.PROHIBITED}
            if sa in good and sb in bad:
                pairs_flagged.append(
                    {
                        "pair": f"{a.value} vs {b.value}",
                        "note": (
                            f"Retrieval-based stance suggests {a.value} may be more permissive or "
                            f"conditionally allowed while {b.value} shows stronger prohibition signals "
                            f"in the cited passages - requires counsel review."
                        ),
                    }
                )
            elif sa in bad and sb in good:
                pairs_flagged.append(
                    {
                        "pair": f"{b.value} vs {a.value}",
                        "note": (
                            f"Retrieval-based stance suggests {b.value} may be more permissive or "
                            f"conditionally allowed while {a.value} shows stronger prohibition signals "
                            f"in the cited passages - requires counsel review."
                        ),
                    }
                )

    divergence_summary = None
    if pairs_flagged:
        divergence_summary = (
            f"Detected {len(pairs_flagged)} jurisdiction pair(s) with divergent coarse stances "
            f"under the current retrieval window."
        )

    return CrossJurisdictionResult(
        by_jurisdiction=by_j,
        divergence_summary=divergence_summary,
        pairs_flagged=pairs_flagged,
    )
