import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  TrendingUp, FileText, AlertTriangle,
  CheckCircle, Plus, ArrowRight,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button }   from '@/components/ui/Button'
import { Badge }    from '@/components/ui/Badge'
import { RiskBadge } from '@/components/ui/Badge'
import { ROUTES }   from '@/constants/app'
import { useAuth }  from '@/context/AuthContext'
import { formatDate, scoreToColor } from '@/utils/formatters'
import { complianceService } from '@/services/complianceService'
import type { AnalysisHistory } from '@/types/api'

// ── Score ring SVG ─────────────────────────────────────────────
function ScoreRing({ score }: { score: number }) {
  const color = score >= 80 ? '#22C55E' : score >= 60 ? '#F59E0B' : '#EF4444'
  const circumference = 2 * Math.PI * 14  // r=14
  const dash = (score / 100) * circumference

  return (
    <div className="relative w-10 h-10 shrink-0">
      <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="14"
          fill="none" stroke="var(--border)" strokeWidth="3" />
        <circle cx="18" cy="18" r="14"
          fill="none" stroke={color} strokeWidth="3"
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-[10px] font-bold"
        style={{ color }}
      >
        {score}
      </span>
    </div>
  )
}

// ── Quick actions ──────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: 'Run new analysis',  path: ROUTES.ANALYZE,  primary: true },
  { label: 'View all reports',  path: ROUTES.REPORTS },
  { label: 'Browse citations',  path: '/citations' },
  { label: 'Settings',          path: ROUTES.SETTINGS },
]

// ── Component ──────────────────────────────────────────────────
export function DashboardPage() {
  const { user } = useAuth()
  const [history, setHistory] = useState<AnalysisHistory[]>([])

  useEffect(() => {
    let cancelled = false
    complianceService.getHistory().then(rows => {
      if (!cancelled) setHistory(rows)
    }).catch(() => {
      if (!cancelled) setHistory([])
    })
    return () => { cancelled = true }
  }, [])

  const recent = useMemo(() => history.slice(0, 5), [history])

  const chartData = useMemo(() => {
    const byMonth = new Map<string, { month: string; analyses: number; avgScore: number; highRisk: number; _sum: number }>()
    for (const row of history) {
      const d = new Date(row.created_at)
      if (Number.isNaN(d.getTime())) continue
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      const label = d.toLocaleString(undefined, { month: 'short', year: '2-digit' })
      const cur = byMonth.get(key) ?? { month: label, analyses: 0, avgScore: 0, highRisk: 0, _sum: 0 }
      cur.analyses += 1
      cur._sum += row.compliance_score
      if (row.risk_level === 'high') cur.highRisk += 1
      cur.avgScore = Math.round(cur._sum / cur.analyses)
      byMonth.set(key, cur)
    }
    return [...byMonth.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6)
      .map(([, v]) => ({ month: v.month, analyses: v.analyses, avgScore: v.avgScore, highRisk: v.highRisk }))
  }, [history])

  const riskBreakdown = useMemo(() => {
    const counts = { low: 0, medium: 0, high: 0 }
    for (const row of history) {
      if (row.risk_level === 'low' || row.risk_level === 'medium' || row.risk_level === 'high') {
        counts[row.risk_level] += 1
      }
    }
    return [
      { name: 'Low', value: counts.low, fill: '#22C55E' },
      { name: 'Medium', value: counts.medium, fill: '#F59E0B' },
      { name: 'High', value: counts.high, fill: '#EF4444' },
    ].filter(r => r.value > 0)
  }, [history])

  const liveStats = useMemo(() => {
    const total = history.length
    const avg = total
      ? Math.round(history.reduce((s, r) => s + r.compliance_score, 0) / total)
      : 0
    const high = history.filter(r => r.risk_level === 'high').length
    return [
      {
        label: 'Total Analyses',
        value: String(total),
        delta: total ? 'From compliance history' : 'Run an analysis to populate',
        icon:  FileText,
        color: 'text-blue-500',
        bg:    'bg-blue-50 dark:bg-blue-950/40',
      },
      {
        label: 'Avg Compliance Score',
        value: total ? `${avg}%` : '—',
        delta: 'Derived from peak risk',
        icon:  TrendingUp,
        color: 'text-green-500',
        bg:    'bg-green-50 dark:bg-green-950/40',
      },
      {
        label: 'High Risk Items',
        value: String(high),
        delta: 'Analyses tagged high risk',
        icon:  AlertTriangle,
        color: 'text-red-500',
        bg:    'bg-red-50 dark:bg-red-950/40',
      },
      {
        label: 'Resolved Issues',
        value: String(history.filter(r => r.risk_level === 'low').length),
        delta: 'Low-risk analyses',
        icon:  CheckCircle,
        color: 'text-teal-500',
        bg:    'bg-teal-50 dark:bg-teal-950/40',
      },
    ]
  }, [history])

  const hour     = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="space-y-6">

      {/* ── Page header ──────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]">
            {greeting}, {user?.name?.split(' ')[0] ?? 'there'}
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            Here&apos;s your compliance overview for today.
          </p>
        </div>
        <Link to={ROUTES.ANALYZE}>
          <Button leftIcon={<Plus className="w-4 h-4" />}>
            New Analysis
          </Button>
        </Link>
      </div>

      {/* ── Stats grid ───────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {liveStats.map((stat, i) => {
          const Icon = stat.icon
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card padding="md" className="h-full">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--text-muted)] mb-1 truncate">
                      {stat.label}
                    </p>
                    <p className="text-2xl font-bold text-[var(--text)]">
                      {stat.value}
                    </p>
                    <p className="text-xs text-[var(--text-subtle)] mt-1">
                      {stat.delta}
                    </p>
                  </div>
                  <div className={`${stat.bg} p-2.5 rounded-xl shrink-0`}>
                    <Icon className={`w-5 h-5 ${stat.color}`} />
                  </div>
                </div>
              </Card>
            </motion.div>
          )
        })}
      </div>

      {/* ── Chart + Quick actions ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Bar chart — live history */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Analysis Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)] py-16 text-center">
                No history yet — charts populate after you run analyses.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={32} barCategoryGap="30%">
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--border)"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 12, fill: 'var(--text-muted)' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: 'var(--text-muted)' }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'var(--bg-raised)' }}
                    contentStyle={{
                      background:   'var(--bg-surface)',
                      border:       '1px solid var(--border)',
                      borderRadius: '10px',
                      color:        'var(--text)',
                      fontSize:     '12px',
                      boxShadow:    '0 4px 12px rgb(0 0 0 / 0.1)',
                    }}
                  />
                  <Bar dataKey="analyses" name="Analyses" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={i === chartData.length - 1 ? '#2563EB' : '#BFDBFE'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Risk breakdown from live history */}
        <Card>
          <CardHeader>
            <CardTitle>Risk mix</CardTitle>
          </CardHeader>
          <CardContent>
            {riskBreakdown.length === 0 ? (
              <div className="space-y-2">
                <p className="text-sm text-[var(--text-muted)] py-8 text-center">
                  Risk levels appear after analyses.
                </p>
                {QUICK_ACTIONS.slice(0, 2).map(action => (
                  <Link key={action.path} to={action.path}>
                    <Button
                      variant={action.primary ? 'primary' : 'ghost'}
                      className="w-full justify-between"
                      rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      {action.label}
                    </Button>
                  </Link>
                ))}
              </div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <PieChart>
                    <Pie
                      data={riskBreakdown}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={40}
                      outerRadius={65}
                      paddingAngle={2}
                    >
                      {riskBreakdown.map(entry => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background:   'var(--bg-surface)',
                        border:       '1px solid var(--border)',
                        borderRadius: '10px',
                        color:        'var(--text)',
                        fontSize:     '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 mt-2">
                  {QUICK_ACTIONS.slice(0, 2).map(action => (
                    <Link key={action.path} to={action.path}>
                      <Button
                        variant={action.primary ? 'primary' : 'ghost'}
                        className="w-full justify-between"
                        rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                      >
                        {action.label}
                      </Button>
                    </Link>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Recent analyses table ─────────────────────────── */}
      <Card padding="none">
        {/* Table header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h3 className="font-semibold text-[var(--text)]">Recent Analyses</h3>
          <Link to={ROUTES.REPORTS}>
            <Button variant="ghost" size="sm"
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
              View all
            </Button>
          </Link>
        </div>

        {/* Scrollable table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[var(--bg-raised)] border-b border-[var(--border)]">
                {['Query', 'Jurisdiction', 'Score', 'Risk', 'Date'].map(h => (
                  <th key={h}
                    className="px-5 py-2.5 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {recent.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-sm text-[var(--text-muted)] text-center">
                    No analyses yet — run one from Analyze.
                  </td>
                </tr>
              ) : recent.map((row, i) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 + i * 0.05 }}
                  className="hover:bg-[var(--bg-raised)] transition-colors group"
                >
                  <td className="px-5 py-3.5">
                    <p className="text-sm font-medium text-[var(--text)] max-w-[240px] truncate">
                      {row.query}
                    </p>
                  </td>
                  <td className="px-5 py-3.5">
                    <Badge variant="outline">{row.jurisdiction}</Badge>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <ScoreRing score={row.compliance_score} />
                      <span className={`text-xs font-medium ${scoreToColor(row.compliance_score)}`}>
                        {row.compliance_score}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <RiskBadge level={row.risk_level} />
                  </td>
                  <td className="px-5 py-3.5 text-xs text-[var(--text-muted)]">
                    {formatDate(row.created_at)}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}