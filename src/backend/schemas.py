from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ml.schemas import (
    Citation,
    CrossJurisdictionResult,
    Jurisdiction,
    LLMComplianceAnswer,
    RiskScore,
)


class ComplianceAnalyzeRequest(BaseModel):
    """POST /v1/compliance/analyze request body."""

    query: str = Field(..., min_length=3, max_length=4000)
    product_feature: str = Field(..., min_length=2, max_length=2000)
    jurisdictions: list[str] = Field(
        default_factory=lambda: [
            Jurisdiction.GDPR.value,
            Jurisdiction.DPDP.value,
            Jurisdiction.CCPA.value,
        ]
    )
    top_k: int | None = Field(default=None, ge=1, le=24)
    # Optional — when set, retrieval is scoped to that uploaded document's chunks.
    document_id: int | None = Field(default=None, ge=1)


class RiskHeatmapRow(BaseModel):
    citation_id: str
    chunk_id: str
    jurisdiction: str
    risk_level: str
    risk_score: float
    factors: list[str] = Field(default_factory=list)


class ComplianceAnalyzeResponse(BaseModel):
    """POST /v1/compliance/analyze response body (RAG pipeline output)."""

    query: str
    product_feature: str
    citations: list[Citation]
    risk_scores: list[RiskScore]
    risk_heatmap: list[RiskHeatmapRow]
    cross_jurisdiction: CrossJurisdictionResult
    llm: LLMComplianceAnswer
    # Formalized summary score (derived from peak risk_scores — see analysis_summary).
    compliance_score: int
    risk_level: str
    meta: dict[str, Any] = Field(default_factory=dict)


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str
    password: str = Field(..., min_length=6, max_length=200)


class AuthUserOut(BaseModel):
    id: str
    name: str
    email: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserOut


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str
    # Dev convenience only — never expose reset tokens in production email flows.
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=200)


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    title: str | None
    jurisdiction: str
    source_type: str
    sha256: str
    upload_date: datetime | None
    processing_status: str
    error_message: str | None = None


class ChunkSummary(BaseModel):
    id: int
    chunk_index: int
    text: str
    word_count: int
    char_count: int
    vector_reference: str


class SectionSummary(BaseModel):
    id: int
    section_id: int
    heading: str | None
    numeric_id: str | None
    depth: int
    parent_id: int | None
    chunks: list[ChunkSummary] = Field(default_factory=list)


class DocumentDetailResponse(DocumentUploadResponse):
    source_url: str | None = None
    sections: list[SectionSummary] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: list[DocumentUploadResponse]
    total: int


class LegalQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=4000)
    product_feature: str = Field(default="General compliance review", min_length=2, max_length=2000)
    jurisdictions: list[str] = Field(
        default_factory=lambda: [Jurisdiction.GDPR.value, Jurisdiction.DPDP.value, Jurisdiction.CCPA.value]
    )
    document_id: int | None = Field(default=None, ge=1)
    top_k: int | None = Field(default=None, ge=1, le=24)


class LegalQueryResponse(BaseModel):
    question: str
    answer: str
    citations: list[dict]
    risk_scores: list[dict] = Field(default_factory=list)
    cross_jurisdiction: dict | None = None
    refused_insufficient_citations: bool = False
    citation_ids_used: list[str] = Field(default_factory=list)
    response_time: float
    meta: dict = Field(default_factory=dict)


class RiskAnalysisRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=4000)
    product_feature: str = Field(default="General compliance review", min_length=2, max_length=2000)
    jurisdictions: list[str] = Field(
        default_factory=lambda: [Jurisdiction.GDPR.value, Jurisdiction.DPDP.value, Jurisdiction.CCPA.value]
    )
    document_id: int | None = Field(default=None, ge=1)
    top_k: int | None = Field(default=None, ge=1, le=24)


class RiskAnalysisResponse(BaseModel):
    query: str
    product_feature: str
    overall_risk_level: str
    overall_risk_score: float
    risk_scores: list[dict]
    risk_heatmap: list[dict]
    citations: list[dict]
    response_time: float
    meta: dict = Field(default_factory=dict)


class DeleteResponse(BaseModel):
    id: int
    deleted: bool
    message: str


class AnalysisHistoryItem(BaseModel):
    """Shape expected by the frontend Reports / Dashboard pages."""

    id: str
    query: str
    jurisdiction: str
    compliance_score: int
    risk_level: str
    created_at: str
