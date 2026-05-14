from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import Jurisdiction, RetrievedPassage, RiskLevel, RiskScore

# High-signal compliance language (English corpora; extend per locale).
_PROHIBIT = re.compile(
    r"\b("
    r"prohibited|shall not|must not|may not|not permitted|"
    r"without.*consent|unlawful processing|ban on"
    r")\b",
    re.I,
)
_OBLIGATION = re.compile(
    r"\b("
    r"shall|must ensure|data controller shall|business shall|"
    r"reasonable security|purpose limitation|data minimi[sz]ation|"
    r"notice and|opt-?out|right to (delete|erasure|correct)"
    r")\b",
    re.I,
)
_PENALTY = re.compile(r"\b(fine|penalt(y|ies)|infringement|enforcement|sanction)\b", re.I)
_SENSITIVE = re.compile(
    r"\b(sensitive personal|special categories|biometric|genetic|health data|"
    r"sexual orientation|racial|ethnic origin)\b",
    re.I,
)


@dataclass(frozen=True)
class _LexiconHit:
    name: str
    weight: float


def score_passage(passage: RetrievedPassage) -> RiskScore:
    """
    Explainable heuristic risk: not a substitute for counsel; drives ranking and heatmaps.
    """
    text = passage.text
    factors: list[str] = []
    raw = 0.0

    for pat, name, w in (
        (_PROHIBIT, "prohibition_or_hard_limit_language", 0.42),
        (_PENALTY, "penalty_or_enforcement_language", 0.18),
        (_OBLIGATION, "strict_obligation_language", 0.22),
        (_SENSITIVE, "sensitive_data_category_language", 0.28),
    ):
        if pat.search(text):
            factors.append(name)
            raw += w

    # Jurisdiction prior: EU text tends to be more prescriptive in mixed corpora (weak nudge).
    if passage.jurisdiction == Jurisdiction.GDPR and _OBLIGATION.search(text):
        raw += 0.05
        factors.append("eu_prescriptive_context_prior")

    raw = min(1.0, raw)
    if raw >= 0.55:
        level = RiskLevel.HIGH
    elif raw >= 0.28:
        level = RiskLevel.MEDIUM
    else:
        level = RiskLevel.LOW

    return RiskScore(
        chunk_id=passage.chunk_id,
        jurisdiction=passage.jurisdiction,
        level=level,
        score=raw,
        factors=sorted(set(factors)),
    )
