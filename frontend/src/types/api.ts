// TypeScript types that mirror the FastAPI response schemas exactly.
// These form the contract between frontend and backend.

export interface Jurisdiction {
  code: string
  name: string
  country: string
  description?: string
}

export interface Citation {
  id: string
  title: string
  section: string
  excerpt: string
  source: string
  url?: string
  relevance_score: number
}

export interface RiskItem {
  id: string
  category: string
  description: string
  level: 'high' | 'medium' | 'low' | 'none'
  affected_sections: string[]
  recommendation: string
}

export interface ComplianceResult {
  id: string
  query: string
  jurisdiction: string
  created_at: string
  compliance_score: number        // 0–100
  confidence_score: number        // 0–1
  summary: string
  applicable_laws: string[]
  citations: Citation[]
  risk_items: RiskItem[]
  recommendations: string[]
  processing_time_ms: number
}

export interface AnalyzeRequest {
  query: string
  jurisdiction: string
  document_text?: string
}

export interface AnalyzeResponse {
  success: boolean
  data: ComplianceResult
  message?: string
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  version: string
  uptime_seconds: number
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