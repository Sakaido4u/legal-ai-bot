from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Jurisdiction(str, Enum):
    GDPR = "GDPR"  # EU
    DPDP = "DPDP"  # India
    CCPA = "CCPA"  # US California


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplianceStance(str, Enum):
    """Coarse stance for a product feature under one jurisdiction (retrieval-driven)."""

    ALLOWED = "allowed"
    RESTRICTED = "restricted"
    PROHIBITED = "prohibited"
    UNCLEAR = "unclear"


class Citation(BaseModel):
    """Every model-facing fact should map to one or more citations."""

    citation_id: str = Field(..., description="Stable id, e.g. C0, C1")
    jurisdiction: Jurisdiction
    source_label: str = Field(..., description="Human-readable source, URL path, or statute label")
    heading: str | None = None
    excerpt: str = Field(..., max_length=2000)
    similarity: float = Field(..., ge=0.0, le=1.0)


class ChunkRecord(BaseModel):
    """One embeddable unit tied to a jurisdiction and traceable source."""

    chunk_id: str
    jurisdiction: Jurisdiction
    source_label: str
    heading: str | None = None
    text: str


class RetrievedPassage(BaseModel):
    chunk_id: str
    jurisdiction: Jurisdiction
    source_label: str
    heading: str | None
    text: str
    similarity: float


class RiskScore(BaseModel):
    chunk_id: str
    jurisdiction: Jurisdiction
    level: RiskLevel
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized risk 0–1")
    factors: list[str] = Field(default_factory=list)


class JurisdictionComparison(BaseModel):
    jurisdiction: Jurisdiction
    stance: ComplianceStance
    confidence: float = Field(..., ge=0.0, le=1.0)
    top_citation_ids: list[str] = Field(default_factory=list)


class CrossJurisdictionResult(BaseModel):
    """High-level matrix for dashboards (heatmap / diff)."""

    by_jurisdiction: dict[str, JurisdictionComparison]
    divergence_summary: str | None = None
    pairs_flagged: list[dict[str, str]] = Field(
        default_factory=list,
        description="e.g. [{'pair': 'DPDP vs GDPR', 'note': '...'}]",
    )


class LLMComplianceAnswer(BaseModel):
    """Strict citation mode: if no grounded passages, answer must be empty / refusal."""

    answer_text: str
    citation_ids_used: list[str] = Field(default_factory=list)
    refused_insufficient_citations: bool = False
