from __future__ import annotations

from dataclasses import dataclass

from .schemas import RetrievedPassage


@dataclass(frozen=True)
class EvidenceAssessment:
    """Single source of truth for whether retrieval supports a scored answer."""

    sufficient: bool
    low_confidence: bool
    max_similarity: float
    passage_count: int
    passages: list[RetrievedPassage]


def assess_evidence(
    passages: list[RetrievedPassage],
    *,
    min_score: float = 0.22,
    min_passages: int = 1,
    confidence_floor: float = 0.50,
) -> EvidenceAssessment:
    """
    Decide whether retrieved passages are strong enough to answer + score.

    - insufficient → refuse summary AND suppress risk verdict
    - sufficient but below confidence_floor → answer/score OK, flag low_confidence
    """
    usable = [p for p in passages if float(p.similarity) >= min_score]
    max_sim = max((float(p.similarity) for p in usable), default=0.0)
    sufficient = len(usable) >= min_passages
    low_confidence = sufficient and max_sim < confidence_floor
    return EvidenceAssessment(
        sufficient=sufficient,
        low_confidence=low_confidence,
        max_similarity=max_sim,
        passage_count=len(usable),
        passages=usable,
    )
