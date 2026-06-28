import api from '@/api/axiosInstance'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ComplianceResult,
  Jurisdiction,
  HealthResponse,
  AnalysisHistory,
} from '@/types/api'

// ── Compliance Service ────────────────────────────────────────
// All methods map 1:1 to a FastAPI endpoint.
// Components import from here — never call api.post() directly.

export const complianceService = {

  // POST /v1/compliance/analyze
  async analyze(request: AnalyzeRequest): Promise<ComplianceResult> {
    const res = await api.post<AnalyzeResponse>('/v1/compliance/analyze', request)
    if (!res.data.success) {
      throw new Error(res.data.message ?? 'Analysis failed')
    }
    return res.data.data
  },

  // GET /v1/compliance/jurisdictions
  async getJurisdictions(): Promise<Jurisdiction[]> {
    const res = await api.get<Jurisdiction[]>('/v1/compliance/jurisdictions')
    return res.data
  },

  // GET /v1/compliance/history  (future endpoint)
  async getHistory(): Promise<AnalysisHistory[]> {
    try {
      const res = await api.get<AnalysisHistory[]>('/v1/compliance/history')
      return res.data
    } catch {
      // Return mock data if endpoint not yet implemented
      return MOCK_HISTORY
    }
  },
}

// ── Health Service ─────────────────────────────────────────────
export const healthService = {
  // GET /health
  async check(): Promise<HealthResponse> {
    const res = await api.get<HealthResponse>('/health')
    return res.data
  },
}

// ── Mock data (used when backend is not running) ───────────────
export const MOCK_HISTORY: AnalysisHistory[] = [
  { id: '1', query: 'GDPR data processing agreement',   jurisdiction: 'EU', compliance_score: 82, risk_level: 'low',    created_at: '2025-06-10T10:30:00Z' },
  { id: '2', query: 'Employment contract termination',  jurisdiction: 'IN', compliance_score: 61, risk_level: 'medium', created_at: '2025-06-09T14:20:00Z' },
  { id: '3', query: 'Software licensing fair use',      jurisdiction: 'US', compliance_score: 45, risk_level: 'high',   created_at: '2025-06-07T09:15:00Z' },
  { id: '4', query: 'NDA confidentiality provisions',   jurisdiction: 'UK', compliance_score: 91, risk_level: 'low',    created_at: '2025-06-05T16:45:00Z' },
  { id: '5', query: 'Patent infringement analysis',     jurisdiction: 'US', compliance_score: 73, risk_level: 'medium', created_at: '2025-06-01T11:00:00Z' },
]

export const MOCK_JURISDICTIONS: Jurisdiction[] = [
  { code: 'IN', name: 'India',          country: 'India' },
  { code: 'US', name: 'United States',  country: 'United States' },
  { code: 'EU', name: 'European Union', country: 'European Union' },
  { code: 'UK', name: 'United Kingdom', country: 'United Kingdom' },
]