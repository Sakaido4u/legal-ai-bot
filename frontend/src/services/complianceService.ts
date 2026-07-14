import api from '@/api/axiosInstance'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  Jurisdiction,
  HealthResponse,
  AnalysisHistory,
} from '@/types/api'

// ── Compliance Service ────────────────────────────────────────
// All methods map 1:1 to a FastAPI endpoint.
// Components import from here — never call api.post() directly.

export const complianceService = {

  // POST /v1/compliance/analyze
  async analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
    // Analysis + LLM can exceed the default 30s timeout.
    const res = await api.post<AnalyzeResponse>(
      '/v1/compliance/analyze',
      request,
      { timeout: 180_000 },
    )
    return res.data
  },

  // GET /v1/compliance/jurisdictions → { jurisdictions: string[] }
  async getJurisdictions(): Promise<Jurisdiction[]> {
    const res = await api.get<{ jurisdictions: string[] }>('/v1/compliance/jurisdictions')
    const codes = res.data.jurisdictions ?? []
    return codes.map(code => ({
      code,
      name: code,
      country:
        code === 'GDPR' ? 'European Union'
        : code === 'DPDP' ? 'India'
        : code === 'CCPA' ? 'United States'
        : code,
    }))
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

/** Fallback when /v1/compliance/jurisdictions is unreachable — must match backend Jurisdiction enum. */
export const MOCK_JURISDICTIONS: Jurisdiction[] = [
  { code: 'GDPR', name: 'GDPR', country: 'European Union' },
  { code: 'DPDP', name: 'DPDP', country: 'India' },
  { code: 'CCPA', name: 'CCPA', country: 'United States' },
]