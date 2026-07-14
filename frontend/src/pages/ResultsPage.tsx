import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Download, ArrowLeft, BookOpen, AlertTriangle,
  CheckCircle, Info, Clock, Shield,
} from 'lucide-react'
import {
  RadialBarChart, RadialBar, ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip,
} from 'recharts'
import { Button }    from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Badge }     from '@/components/ui/Badge'
import { RiskBadge } from '@/components/ui/Badge'
import { Skeleton, SkeletonCard } from '@/components/ui/Skeleton'
import { complianceService } from '@/services/complianceService'
import type {
  AnalyzeResponse,
  LegalQueryResponse,
  RiskAnalysisResponse,
  RiskScore,
  StoredAnalysis,
} from '@/types/api'
import { formatDate, scoreToLabel } from '@/utils/formatters'
import { ROUTES } from '@/constants/app'
import { cn } from '@/utils/cn'
import type { RiskLevel } from '@/constants/app'

// ── Demo payload (backend AnalyzeResponse shape) ──────────────
const DEMO_RESULT: AnalyzeResponse = {
  query: 'Marketing emails to EU users with 3-year retention — GDPR compliant?',
  product_feature: 'Marketing emails to EU users with 3-year retention — GDPR compliant?',
  citations: [
    {
      citation_id: 'C0',
      jurisdiction: 'GDPR',
      source_label: 'GDPR Art. 5(1)(e)',
      heading: 'Storage limitation',
      excerpt: 'Personal data shall be kept no longer than is necessary for the purposes for which the personal data are processed.',
      similarity: 0.91,
    },
    {
      citation_id: 'C1',
      jurisdiction: 'GDPR',
      source_label: 'GDPR Art. 7',
      heading: 'Conditions for consent',
      excerpt: 'Consent must be freely given, specific, informed and unambiguous.',
      similarity: 0.87,
    },
  ],
  risk_scores: [
    {
      chunk_id: 'demo-1',
      jurisdiction: 'GDPR',
      level: 'high',
      score: 0.82,
      factors: ['long retention', 'marketing processing'],
    },
    {
      chunk_id: 'demo-2',
      jurisdiction: 'GDPR',
      level: 'medium',
      score: 0.55,
      factors: ['consent requirements'],
    },
  ],
  risk_heatmap: [
    {
      citation_id: 'C0',
      chunk_id: 'demo-1',
      jurisdiction: 'GDPR',
      risk_level: 'high',
      risk_score: 0.82,
      factors: ['long retention', 'marketing processing'],
    },
  ],
  cross_jurisdiction: {
    by_jurisdiction: {
      GDPR: {
        jurisdiction: 'GDPR',
        stance: 'restricted',
        confidence: 0.84,
        top_citation_ids: ['C0', 'C1'],
      },
    },
    divergence_summary: null,
    pairs_flagged: [],
  },
  llm: {
    answer_text:
      'Retrieved passages indicate storage-limitation and consent constraints under GDPR for long-retention marketing [C0][C1]. This is not formal legal advice.',
    citation_ids_used: ['C0', 'C1'],
    refused_insufficient_citations: false,
  },
  compliance_score: 18,
  risk_level: 'high',
  meta: { index_total_vectors: 42, retrieval_min_score: 0.25, score_method: '100 - peak_risk*100' },
}

function ExtraEndpointsPanel({ result }: { result: AnalyzeResponse }) {
  const [tab, setTab] = useState<'legal_query' | 'risk_analysis'>('legal_query')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [legal, setLegal] = useState<LegalQueryResponse | null>(null)
  const [risk, setRisk] = useState<RiskAnalysisResponse | null>(null)

  const jurisdictions = Object.keys(result.cross_jurisdiction.by_jurisdiction)
  const documentId =
    typeof result.meta.document_id === 'number' ? result.meta.document_id : null

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      if (tab === 'legal_query') {
        const data = await complianceService.legalQuery({
          question: result.query,
          product_feature: result.product_feature,
          jurisdictions: jurisdictions.length ? jurisdictions : ['GDPR'],
          document_id: documentId,
        })
        setLegal(data)
      } else {
        const data = await complianceService.riskAnalysis({
          query: result.query,
          product_feature: result.product_feature,
          jurisdictions: jurisdictions.length ? jurisdictions : ['GDPR'],
          document_id: documentId,
        })
        setRisk(data)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Extra endpoints</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-xs text-[var(--text-muted)]">
          Re-run the same query through <code className="font-mono">/legal_query</code> or{' '}
          <code className="font-mono">/risk_analysis</code>
          {documentId ? ` (scoped to doc #${documentId})` : ''}.
        </p>

        <div className="flex flex-wrap gap-2">
          {(['legal_query', 'risk_analysis'] as const).map(t => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors',
                tab === t
                  ? 'bg-brand-600 text-white border-brand-600'
                  : 'border-[var(--border)] text-[var(--text-muted)] hover:bg-[var(--bg-raised)]',
              )}
            >
              {t === 'legal_query' ? 'Legal query' : 'Risk analysis'}
            </button>
          ))}
          <Button
            type="button"
            size="sm"
            onClick={() => void run()}
            isLoading={loading}
          >
            {loading ? 'Calling…' : 'Run endpoint'}
          </Button>
        </div>

        {error && (
          <p className="text-xs text-red-500 flex items-start gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            {error}
          </p>
        )}

        {tab === 'legal_query' && legal && (
          <div className="space-y-2 rounded-xl border border-[var(--border)] p-4 bg-[var(--bg-raised)]">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">{legal.response_time}s</Badge>
              {legal.refused_insufficient_citations && (
                <Badge variant="warning">Insufficient citations</Badge>
              )}
            </div>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed whitespace-pre-wrap">
              {legal.answer || '(empty answer)'}
            </p>
            <p className="text-xs text-[var(--text-subtle)]">
              Citations: {legal.citations.length} · Risk rows: {legal.risk_scores.length}
            </p>
          </div>
        )}

        {tab === 'risk_analysis' && risk && (
          <div className="space-y-3 rounded-xl border border-[var(--border)] p-4 bg-[var(--bg-raised)]">
            <div className="flex items-center gap-2 flex-wrap">
              <RiskBadge
                level={
                  (['high', 'medium', 'low'].includes(risk.overall_risk_level)
                    ? risk.overall_risk_level
                    : 'medium') as RiskLevel
                }
              />
              <Badge variant="outline">
                score {Math.round(risk.overall_risk_score * 100)}%
              </Badge>
              <Badge variant="outline">{risk.response_time}s</Badge>
            </div>
            <ul className="space-y-1.5">
              {risk.risk_scores.slice(0, 5).map((rs, i) => (
                <li key={`${rs.chunk_id}-${i}`} className="text-xs text-[var(--text-muted)]">
                  <span className="font-semibold text-[var(--text)]">{rs.jurisdiction}</span>
                  {' · '}{rs.level}{' · '}{Math.round(rs.score * 100)}%
                  {rs.factors.length ? ` — ${rs.factors.join(', ')}` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

/** Invert peak risk → 0–100 display score (higher = lower peak risk). */
function maxRiskScore(scores: RiskScore[]): number {
  if (!scores.length) return 0
  return Math.max(...scores.map(s => s.score))
}

function riskToComplianceDisplay(scores: RiskScore[]): number {
  return Math.round((1 - maxRiskScore(scores)) * 100)
}

function avgConfidence(result: AnalyzeResponse): number {
  const values = Object.values(result.cross_jurisdiction.by_jurisdiction).map(j => j.confidence)
  if (!values.length) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 80 ? '#22C55E' : score >= 60 ? '#F59E0B' : '#EF4444'
  const label = scoreToLabel(score)
  const data  = [{ value: score, fill: color }]

  return (
    <div className="flex flex-col items-center py-4">
      <div className="relative w-44 h-44">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%" cy="50%"
            innerRadius="65%" outerRadius="95%"
            data={data}
            startAngle={220}
            endAngle={-40}
          >
            <RadialBar
              dataKey="value"
              cornerRadius={10}
              background={{ fill: 'var(--border)' }}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-black" style={{ color }}>
            {score}
          </span>
          <span className="text-xs text-[var(--text-muted)] mt-0.5">/ 100</span>
        </div>
      </div>
      <span
        className="mt-1 text-sm font-semibold px-3 py-1 rounded-full"
        style={{ color, background: `${color}15` }}
      >
        {label}
      </span>
      <p className="text-[0.65rem] text-[var(--text-subtle)] mt-2 text-center max-w-[12rem]">
        Backend compliance_score (100 − peak risk × 100)
      </p>
    </div>
  )
}

function RiskChart({ riskScores }: { riskScores: RiskScore[] }) {
  const counts = {
    High:   riskScores.filter(r => r.level === 'high').length,
    Medium: riskScores.filter(r => r.level === 'medium').length,
    Low:    riskScores.filter(r => r.level === 'low').length,
  }
  const data   = Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))
  const COLORS = ['#EF4444', '#F59E0B', '#22C55E']

  return (
    <div className="flex items-center gap-4">
      <ResponsiveContainer width={80} height={80}>
        <PieChart>
          <Pie data={data} dataKey="value" cx="50%" cy="50%"
            innerRadius={22} outerRadius={38} paddingAngle={3}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontSize: '11px',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-1">
        {Object.entries(counts).map(([label, count], i) => (
          <div key={label} className="flex items-center gap-2 text-xs">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ background: COLORS[i] }}
            />
            <span className="text-[var(--text-muted)]">{label}:</span>
            <span className="font-semibold text-[var(--text)]">{count}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function parseStored(raw: string): StoredAnalysis | null {
  try {
    const parsed = JSON.parse(raw) as StoredAnalysis | AnalyzeResponse
    if ('result' in parsed && parsed.result && typeof parsed.result === 'object') {
      return parsed as StoredAnalysis
    }
    // Legacy / raw AnalyzeResponse
    return {
      id: 'session',
      created_at: new Date().toISOString(),
      result: parsed as AnalyzeResponse,
    }
  } catch {
    return null
  }
}

export function ResultsPage() {
  const { id }        = useParams<{ id: string }>()
  const navigate      = useNavigate()
  const [stored, setStored] = useState<StoredAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const raw = sessionStorage.getItem('lexai-last-result')
    if (raw) {
      setStored(parseStored(raw) ?? {
        id: 'demo',
        created_at: new Date().toISOString(),
        result: DEMO_RESULT,
      })
    } else {
      setStored({
        id: 'demo',
        created_at: new Date().toISOString(),
        result: DEMO_RESULT,
      })
    }
    const t = setTimeout(() => setLoading(false), 400)
    return () => clearTimeout(t)
  }, [id])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-9 rounded-lg" />
          <Skeleton className="h-7 w-48" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <SkeletonCard />
          <div className="lg:col-span-2"><SkeletonCard /></div>
        </div>
        <SkeletonCard />
        <SkeletonCard />
      </div>
    )
  }

  if (!stored) return null

  const result = stored.result
  const displayScore =
    typeof result.compliance_score === 'number'
      ? result.compliance_score
      : riskToComplianceDisplay(result.risk_scores)
  const confidence = avgConfidence(result)
  const highRisk = result.risk_scores.filter(r => r.level === 'high').length
  const medRisk = result.risk_scores.filter(r => r.level === 'medium').length
  const jurisdictions = Object.keys(result.cross_jurisdiction.by_jurisdiction)
  const summary = result.llm.refused_insufficient_citations
    ? 'Insufficient grounded citations to produce an answer. Upload / ingest corpus content and try again.'
    : (result.llm.answer_text || 'No LLM summary returned.')
  const factors = [...new Set(result.risk_scores.flatMap(r => r.factors))]
  const divergence = result.cross_jurisdiction.divergence_summary

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate(-1)}
            className="shrink-0 mt-0.5"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-[var(--text)]">
              Analysis Results
            </h1>
            <p className="text-sm text-[var(--text-muted)] mt-0.5 line-clamp-1 max-w-sm">
              {result.query}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-10 sm:ml-0 flex-wrap">
          {jurisdictions.map(j => (
            <Badge key={j} variant="outline">{j}</Badge>
          ))}
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Download className="w-4 h-4" />}
          >
            Export PDF
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--text-muted)]">
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          Analyzed {formatDate(stored.created_at)}
        </span>
        <span className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5" />
          Confidence: {Math.round(confidence * 100)}%
        </span>
        {typeof result.meta.index_total_vectors === 'number' && (
          <span className="flex items-center gap-1.5">
            Index vectors: {result.meta.index_total_vectors}
          </span>
        )}
        {result.meta.document_scoped && (
          <span className="flex items-center gap-1.5">
            Scoped to doc #{String(result.meta.document_id)}
            {typeof result.meta.passages_found === 'number'
              ? ` · ${result.meta.passages_found} passages`
              : ''}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card className="flex flex-col items-center">
          <p className="text-sm font-semibold text-[var(--text-muted)] mb-2 self-start">
            Risk-adjusted score
          </p>
          <ScoreGauge score={displayScore} />
          <div className="w-full pt-4 mt-2 border-t border-[var(--border)]">
            <RiskChart riskScores={result.risk_scores} />
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Evidence-linked summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed mb-5">
              {summary}
            </p>

            {(highRisk > 0 || medRisk > 0) && (
              <div className="flex items-center gap-3 mb-5">
                {highRisk > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900/40">
                    <AlertTriangle className="w-4 h-4 text-red-500" />
                    <span className="text-xs font-semibold text-red-600 dark:text-red-400">
                      {highRisk} High Risk
                    </span>
                  </div>
                )}
                {medRisk > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/40">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                      {medRisk} Medium Risk
                    </span>
                  </div>
                )}
              </div>
            )}

            {result.llm.citation_ids_used.length > 0 && (
              <>
                <p className="text-xs font-bold text-[var(--text)] uppercase tracking-wider mb-3">
                  Citations used by LLM
                </p>
                <ul className="space-y-2">
                  {result.llm.citation_ids_used.map(cid => (
                    <li key={cid} className="flex items-start gap-2.5 text-sm">
                      <CheckCircle className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                      <span className="text-[var(--text-muted)] leading-snug">{cid}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {divergence && (
              <p className="mt-4 text-sm text-[var(--text-muted)] leading-relaxed">
                <span className="font-semibold text-[var(--text)]">Cross-jurisdiction: </span>
                {divergence}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-base font-bold text-[var(--text)] mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Risk scores
          <Badge variant="default" className="ml-1">
            {result.risk_scores.length} items
          </Badge>
        </h2>

        <div className="space-y-3">
          {result.risk_scores.map((item, i) => (
            <motion.div
              key={`${item.chunk_id}-${i}`}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.3 }}
            >
              <Card padding="md">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <RiskBadge level={item.level} />
                      <span className="text-sm font-semibold text-[var(--text)]">
                        {item.jurisdiction}
                      </span>
                      <Badge variant="outline">
                        score {Math.round(item.score * 100)}%
                      </Badge>
                    </div>
                    <p className="text-xs font-mono text-[var(--text-muted)] shrink-0">
                      {item.chunk_id}
                    </p>
                  </div>

                  {item.factors.length > 0 && (
                    <div className="flex items-start gap-2.5 bg-[var(--bg-raised)] rounded-xl p-3">
                      <Info className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
                      <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                        <span className="font-semibold text-[var(--text)]">Factors: </span>
                        {item.factors.join(' · ')}
                      </p>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      {factors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              Risk factors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2.5">
              {factors.map((rec, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm">
                  <span className="text-xs font-mono text-brand-600 shrink-0 mt-0.5 w-5">
                    {i + 1}.
                  </span>
                  <span className="text-[var(--text-muted)] leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-brand-500" />
            Jurisdiction stance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-[var(--border)]">
            {Object.values(result.cross_jurisdiction.by_jurisdiction).map((row, i) => (
              <div key={row.jurisdiction} className="flex items-center justify-between py-3 gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono text-brand-600 shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span className="text-sm font-medium text-[var(--text)]">
                    {row.jurisdiction}
                  </span>
                  <Badge variant="outline">{row.stance}</Badge>
                </div>
                <span className="text-xs text-[var(--text-muted)]">
                  {Math.round(row.confidence * 100)}% confidence
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-purple-500" />
            Legal Citations
            <Badge variant="primary">{result.citations.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {result.citations.map((cite, i) => (
              <motion.div
                key={cite.citation_id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className="p-4 rounded-xl bg-[var(--bg-raised)] border border-[var(--border)]"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">
                      {cite.source_label}
                    </p>
                    <p className="text-xs text-brand-600 font-medium mt-0.5">
                      {cite.heading ?? cite.citation_id} · {cite.jurisdiction}
                    </p>
                  </div>
                  <Badge variant="default">
                    {Math.round(cite.similarity * 100)}% match
                  </Badge>
                </div>
                <blockquote className="text-sm text-[var(--text-muted)] italic border-l-2 border-brand-400 pl-3 leading-relaxed">
                  "{cite.excerpt}"
                </blockquote>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      <ExtraEndpointsPanel result={result} />

      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <Link to={ROUTES.ANALYZE} className="w-full sm:w-auto">
          <Button variant="outline" className="w-full">
            Run Another Analysis
          </Button>
        </Link>
        <Link to={`/citations/${stored.id}`} className="w-full sm:w-auto">
          <Button variant="secondary" className="w-full">
            <BookOpen className="w-4 h-4" />
            View Full Citations
          </Button>
        </Link>
        <Button
          leftIcon={<Download className="w-4 h-4" />}
          className="w-full sm:w-auto"
        >
          Export PDF Report
        </Button>
      </div>
    </div>
  )
}
