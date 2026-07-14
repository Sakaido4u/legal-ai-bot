import api from '@/api/axiosInstance'
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  Jurisdiction,
  HealthResponse,
  AnalysisHistory,
  LegalQueryRequest,
  LegalQueryResponse,
  RiskAnalysisRequest,
  RiskAnalysisResponse,
  StoredAnalysis,
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

  // POST /legal_query
  async legalQuery(request: LegalQueryRequest): Promise<LegalQueryResponse> {
    const res = await api.post<LegalQueryResponse>('/legal_query', request, {
      timeout: 180_000,
    })
    return res.data
  },

  // POST /risk_analysis
  async riskAnalysis(request: RiskAnalysisRequest): Promise<RiskAnalysisResponse> {
    const res = await api.post<RiskAnalysisResponse>('/risk_analysis', request, {
      timeout: 180_000,
    })
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

  // GET /v1/compliance/history
  async getHistory(): Promise<AnalysisHistory[]> {
    const res = await api.get<AnalysisHistory[]>('/v1/compliance/history')
    return res.data
  },

  // GET /v1/compliance/history/{id} — full payload for Results / Citations
  async getAnalysis(id: string): Promise<StoredAnalysis> {
    const res = await api.get<StoredAnalysis>(`/v1/compliance/history/${id}`)
    return res.data
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

/** Fallback when /v1/compliance/jurisdictions is unreachable — must match backend Jurisdiction enum. */
export const MOCK_JURISDICTIONS: Jurisdiction[] = [
  { code: 'GDPR', name: 'GDPR', country: 'European Union' },
  { code: 'DPDP', name: 'DPDP', country: 'India' },
  { code: 'CCPA', name: 'CCPA', country: 'United States' },
]
