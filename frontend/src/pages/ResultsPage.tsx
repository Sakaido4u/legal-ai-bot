import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Download, ArrowLeft, BookOpen, AlertTriangle,
  CheckCircle, Info, ChevronDown, ChevronUp,
  Clock, Shield, ExternalLink,
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
import type { ComplianceResult } from '@/types/api'
import { cn } from '@/utils/cn'
import { formatDate, formatMs, scoreToColor, scoreToLabel } from '@/utils/formatters'
import { ROUTES } from '@/constants/app'

// ── Mock result (shown if no real result in session) ──────────
const MOCK_RESULT: ComplianceResult = {
  id:               '1',
  query:            'We are processing personal data of EU citizens for marketing purposes with a 3-year retention policy. Are we GDPR compliant?',
  jurisdiction:     'EU',
  created_at:       new Date().toISOString(),
  compliance_score: 74,
  confidence_score: 0.88,
  summary:
    'Your data processing practices show partial GDPR compliance. Key areas require immediate attention: your 3-year data retention policy significantly exceeds recommended limits for marketing data, and your current consent mechanism (pre-ticked boxes) explicitly violates GDPR Article 7. However, your overall data security measures and breach notification procedures are adequate.',
  applicable_laws: [
    'GDPR Article 5(1)(e) — Storage Limitation Principle',
    'GDPR Article 7 — Conditions for Consent',
    'GDPR Article 13 — Information to be Provided',
    'GDPR Article 17 — Right to Erasure ("Right to be Forgotten")',
    'GDPR Article 25 — Data Protection by Design and by Default',
    'GDPR Article 30 — Records of Processing Activities',
  ],
  citations: [
    {
      id:              'c1',
      title:           'General Data Protection Regulation',
      section:         'Article 5(1)(e) — Storage Limitation',
      excerpt:         'Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed.',
      source:          'European Parliament & Council',
      url:             'https://gdpr.eu/article-5/',
      relevance_score: 0.96,
    },
    {
      id:              'c2',
      title:           'GDPR Article 7 — Conditions for Consent',
      section:         'Article 7(2)',
      excerpt:         'If the data subject\'s consent is given in the context of a written declaration which also concerns other matters, the request for consent shall be presented in a manner which is clearly distinguishable.',
      source:          'European Parliament & Council',
      url:             'https://gdpr.eu/article-7/',
      relevance_score: 0.91,
    },
    {
      id:              'c3',
      title:           'ICO Guidance on Marketing',
      section:         'Direct Marketing Retention Periods',
      excerpt:         'The ICO recommends that personal data used solely for direct marketing purposes should not be retained for longer than 12-13 months without refreshing consent.',
      source:          'Information Commissioner\'s Office',
      url:             'https://ico.org.uk/',
      relevance_score: 0.87,
    },
  ],
  risk_items: [
    {
      id:                'r1',
      category:          'Data Retention',
      level:             'high',
      description:       'Your 3-year data retention policy significantly exceeds the ICO-recommended 12-13 months for marketing data under the GDPR storage limitation principle.',
      affected_sections: ['Privacy Policy §3.2', 'Data Processing Agreement §7'],
      recommendation:    'Reduce data retention to 13 months for marketing data and implement automated deletion or anonymization workflows.',
    },
    {
      id:                'r2',
      category:          'Consent Mechanism',
      level:             'high',
      description:       'Pre-ticked consent checkboxes on your signup form are explicitly prohibited under GDPR Article 7. Consent must be freely given, specific, informed, and unambiguous.',
      affected_sections: ['Signup Form', 'Cookie Policy', 'Newsletter Subscription'],
      recommendation:    'Replace all pre-ticked boxes with explicit opt-in checkboxes. Implement granular consent for each data processing purpose.',
    },
    {
      id:                'r3',
      category:          'Documentation',
      level:             'medium',
      description:       'Records of Processing Activities (ROPA) under Article 30 are incomplete and do not cover all current data processing operations.',
      affected_sections: ['Internal Documentation', 'ROPA Register'],
      recommendation:    'Complete and maintain Article 30 records for all data processing activities, including processors and sub-processors.',
    },
    {
      id:                'r4',
      category:          'Data Subject Rights',
      level:             'low',
      description:       'Response time for data subject access requests occasionally exceeds the 30-day statutory limit based on your current process.',
      affected_sections: ['DSAR Procedure'],
      recommendation:    'Implement a ticketing system for DSARs with automatic 30-day deadline tracking and escalation alerts.',
    },
  ],
  recommendations: [
    'Reduce marketing data retention to 13 months and automate deletion',
    'Replace all pre-ticked consent boxes with explicit opt-in mechanisms',
    'Complete ROPA documentation for all data processing activities',
    'Implement a DPO (Data Protection Officer) appointment',
    'Conduct a Data Protection Impact Assessment (DPIA) for high-risk processing',
    'Review and update your Privacy Notice to include all required information',
  ],
  processing_time_ms: 2847,
}

// ── Score Gauge ────────────────────────────────────────────────
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
        {/* Center text */}
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
    </div>
  )
}

// ── Risk distribution mini chart ───────────────────────────────
function RiskChart({ riskItems }: { riskItems: ComplianceResult['risk_items'] }) {
  const counts = {
    High:   riskItems.filter(r => r.level === 'high').length,
    Medium: riskItems.filter(r => r.level === 'medium').length,
    Low:    riskItems.filter(r => r.level === 'low').length,
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

// ── Expandable law item ─────────────────────────────────────────
function LawItem({ law, index }: { law: string; index: number }) {
  const [open, setOpen] = useState(false)
  const parts = law.split('—')
  const title = parts[0]?.trim() ?? law
  const desc  = parts[1]?.trim()

  return (
    <div className="border-b border-[var(--border)] last:border-0">
      <button
        onClick={() => setOpen(p => !p)}
        className="w-full flex items-center justify-between py-3 px-1 text-left hover:bg-[var(--bg-raised)] rounded-lg transition-colors gap-3"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xs font-mono text-brand-600 shrink-0">
            {String(index + 1).padStart(2, '0')}
          </span>
          <span className="text-sm font-medium text-[var(--text)] truncate">
            {title}
          </span>
        </div>
        {desc && (
          open
            ? <ChevronUp className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
            : <ChevronDown className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
        )}
      </button>
      {open && desc && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="px-1 pb-3"
        >
          <p className="text-sm text-[var(--text-muted)] pl-8 leading-relaxed">
            {desc}
          </p>
        </motion.div>
      )}
    </div>
  )
}

// ── Main Component ──────────────────────────────────────────────
export function ResultsPage() {
  const { id }        = useParams<{ id: string }>()
  const navigate      = useNavigate()
  const [result,    setResult]  = useState<ComplianceResult | null>(null)
  const [loading,   setLoading] = useState(true)

  useEffect(() => {
    const stored = sessionStorage.getItem('lexai-last-result')
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as ComplianceResult
        setResult(parsed)
      } catch {
        setResult(MOCK_RESULT)
      }
    } else {
      setResult(MOCK_RESULT)
    }
    const t = setTimeout(() => setLoading(false), 400)
    return () => clearTimeout(t)
  }, [id])

  // ── Loading skeleton ─────────────────────────────────────────
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

  if (!result) return null

  const highRisk   = result.risk_items.filter(r => r.level === 'high').length
  const medRisk    = result.risk_items.filter(r => r.level === 'medium').length

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* ── Header ───────────────────────────────────────── */}
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
        <div className="flex items-center gap-2 shrink-0 ml-10 sm:ml-0">
          <Badge variant="outline">{result.jurisdiction}</Badge>
          <Button
            variant="outline"
            size="sm"
            leftIcon={<Download className="w-4 h-4" />}
          >
            Export PDF
          </Button>
        </div>
      </div>

      {/* ── Meta info bar ─────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--text-muted)]">
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          Analyzed {formatDate(result.created_at)}
        </span>
        <span className="flex items-center gap-1.5">
          <Shield className="w-3.5 h-3.5" />
          Confidence: {Math.round(result.confidence_score * 100)}%
        </span>
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          Processed in {formatMs(result.processing_time_ms)}
        </span>
      </div>

      {/* ── Score + Summary ───────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Score gauge */}
        <Card className="flex flex-col items-center">
          <p className="text-sm font-semibold text-[var(--text-muted)] mb-2 self-start">
            Compliance Score
          </p>
          <ScoreGauge score={result.compliance_score} />
          <div className="w-full pt-4 mt-2 border-t border-[var(--border)]">
            <RiskChart riskItems={result.risk_items} />
          </div>
        </Card>

        {/* Summary */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-[var(--text-muted)] leading-relaxed mb-5">
              {result.summary}
            </p>

            {/* Risk counts */}
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

            {/* Key recommendations */}
            <p className="text-xs font-bold text-[var(--text)] uppercase tracking-wider mb-3">
              Key Recommendations
            </p>
            <ul className="space-y-2">
              {result.recommendations.slice(0, 4).map((rec, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm">
                  <CheckCircle className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                  <span className="text-[var(--text-muted)] leading-snug">{rec}</span>
                </li>
              ))}
              {result.recommendations.length > 4 && (
                <p className="text-xs text-brand-600 pl-6">
                  +{result.recommendations.length - 4} more recommendations below
                </p>
              )}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* ── Risk Items ────────────────────────────────────── */}
      <div>
        <h2 className="text-base font-bold text-[var(--text)] mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Risk Analysis
          <Badge variant="default" className="ml-1">
            {result.risk_items.length} items
          </Badge>
        </h2>

        <div className="space-y-3">
          {result.risk_items.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.3 }}
            >
              <Card padding="md">
                <div className="space-y-3">
                  {/* Header row */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <RiskBadge level={item.level} />
                      <span className="text-sm font-semibold text-[var(--text)]">
                        {item.category}
                      </span>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-[var(--text-subtle)] mb-1">Affected</p>
                      {item.affected_sections.map(s => (
                        <p key={s} className="text-xs font-mono text-[var(--text-muted)] leading-snug">
                          {s}
                        </p>
                      ))}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                    {item.description}
                  </p>

                  {/* Recommendation */}
                  <div className="flex items-start gap-2.5 bg-[var(--bg-raised)] rounded-xl p-3">
                    <Info className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
                    <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                      <span className="font-semibold text-[var(--text)]">Recommendation: </span>
                      {item.recommendation}
                    </p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ── All Recommendations ───────────────────────────── */}
      {result.recommendations.length > 4 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              All Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2.5">
              {result.recommendations.map((rec, i) => (
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

      {/* ── Applicable Laws ───────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-brand-500" />
            Applicable Laws & Regulations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-[var(--border)]">
            {result.applicable_laws.map((law, i) => (
              <LawItem key={i} law={law} index={i} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── Citations ─────────────────────────────────────── */}
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
                key={cite.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className="p-4 rounded-xl bg-[var(--bg-raised)] border border-[var(--border)]"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <p className="text-sm font-semibold text-[var(--text)]">
                      {cite.title}
                    </p>
                    <p className="text-xs text-brand-600 font-medium mt-0.5">
                      {cite.section}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="default">
                      {Math.round(cite.relevance_score * 100)}% match
                    </Badge>
                    {cite.url && (
                      <a
                        href={cite.url}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1 rounded text-[var(--text-muted)] hover:text-brand-600 transition-colors"
                        title="View source"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
                <blockquote className="text-sm text-[var(--text-muted)] italic border-l-2 border-brand-400 pl-3 leading-relaxed">
                  "{cite.excerpt}"
                </blockquote>
                <p className="text-xs text-[var(--text-subtle)] mt-2">
                  Source: {cite.source}
                </p>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── Actions footer ────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
        <Link to={ROUTES.ANALYZE} className="w-full sm:w-auto">
          <Button variant="outline" className="w-full">
            Run Another Analysis
          </Button>
        </Link>
        <Link to={`/citations/${result.id}`} className="w-full sm:w-auto">
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