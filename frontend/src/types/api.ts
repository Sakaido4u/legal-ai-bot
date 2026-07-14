// TypeScript types that mirror the FastAPI response schemas exactly.
// These form the contract between frontend and backend.

export interface Jurisdiction {
  code: string
  name: string
  country: string
  description?: string
}

/** Backend Jurisdiction enum values used by analyze / upload. */
export type JurisdictionCode = 'GDPR' | 'DPDP' | 'CCPA'

export type RiskLevel = 'low' | 'medium' | 'high'
export type ComplianceStance = 'allowed' | 'restricted' | 'prohibited' | 'unclear'

/** Mirrors ml.schemas.Citation */
export interface Citation {
  citation_id: string
  jurisdiction: JurisdictionCode | string
  source_label: string
  heading: string | null
  excerpt: string
  similarity: number
}

/** Mirrors ml.schemas.RiskScore */
export interface RiskScore {
  chunk_id: string
  jurisdiction: JurisdictionCode | string
  level: RiskLevel
  score: number
  factors: string[]
}

/** Mirrors backend RiskHeatmapRow */
export interface RiskHeatmapRow {
  citation_id: string
  chunk_id: string
  jurisdiction: string
  risk_level: string
  risk_score: number
  factors: string[]
}

/** Mirrors ml.schemas.JurisdictionComparison */
export interface JurisdictionComparison {
  jurisdiction: JurisdictionCode | string
  stance: ComplianceStance
  confidence: number
  top_citation_ids: string[]
}

/** Mirrors ml.schemas.CrossJurisdictionResult */
export interface CrossJurisdictionResult {
  by_jurisdiction: Record<string, JurisdictionComparison>
  divergence_summary: string | null
  pairs_flagged: Array<Record<string, string>>
}

/** Mirrors ml.schemas.LLMComplianceAnswer */
export interface LLMComplianceAnswer {
  answer_text: string
  citation_ids_used: string[]
  refused_insufficient_citations: boolean
}

/**
 * POST /v1/compliance/analyze — request body
 * (ComplianceAnalyzeRequest)
 */
export interface AnalyzeRequest {
  query: string
  product_feature: string
  jurisdictions: string[]
  top_k?: number | null
  /** Optional uploaded document to scope retrieval / ground the answer. */
  document_id?: number | null
}

/**
 * POST /v1/compliance/analyze — response body
 * (ComplianceAnalyzeResponse). Returned directly — no { success, data } wrapper.
 */
export interface AnalyzeResponse {
  query: string
  product_feature: string
  citations: Citation[]
  risk_scores: RiskScore[]
  risk_heatmap: RiskHeatmapRow[]
  cross_jurisdiction: CrossJurisdictionResult
  llm: LLMComplianceAnswer
  /** Backend summary score: 100 − peak risk×100 (formalized Phase 3.3). */
  compliance_score: number
  risk_level: RiskLevel | string
  meta: {
    index_total_vectors?: number
    retrieval_min_score?: number
    document_id?: number | null
    document_scoped?: boolean
    passages_found?: number
    score_method?: string
    [key: string]: unknown
  }
}

/** Client-only wrapper for sessionStorage / results routing. */
export interface StoredAnalysis {
  id: string
  created_at: string
  result: AnalyzeResponse
}

export interface HealthResponse {
  status: 'ok' | 'healthy' | 'degraded' | 'unhealthy' | 'starting'
  version?: string
  uptime_seconds?: number
  index_vectors?: number
  embedding_model?: string | null
  llm_provider?: string
  llm_model?: string
}

export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
}

// History item for Reports page
export interface AnalysisHistory {
  id: string
  query: string
  jurisdiction: string
  compliance_score: number
  risk_level: 'high' | 'medium' | 'low' | 'none'
  created_at: string
}

/** Mirrors backend DocumentUploadResponse (POST /documents/upload). */
export interface DocumentUploadResponse {
  id: number
  filename: string
  title: string | null
  jurisdiction: string
  source_type: string
  sha256: string
  upload_date: string | null
  processing_status: string
  error_message: string | null
}

/** POST /legal_query */
export interface LegalQueryRequest {
  question: string
  product_feature?: string
  jurisdictions: string[]
  document_id?: number | null
  top_k?: number | null
}

export interface LegalQueryResponse {
  question: string
  answer: string
  citations: Citation[]
  risk_scores: RiskScore[]
  cross_jurisdiction: CrossJurisdictionResult | null
  refused_insufficient_citations: boolean
  citation_ids_used: string[]
  response_time: number
  meta: Record<string, unknown>
}

/** POST /risk_analysis */
export interface RiskAnalysisRequest {
  query: string
  product_feature?: string
  jurisdictions: string[]
  document_id?: number | null
  top_k?: number | null
}

export interface RiskAnalysisResponse {
  query: string
  product_feature: string
  overall_risk_level: string
  overall_risk_score: number
  risk_scores: RiskScore[]
  risk_heatmap: RiskHeatmapRow[]
  citations: Citation[]
  response_time: number
  meta: Record<string, unknown>
}
