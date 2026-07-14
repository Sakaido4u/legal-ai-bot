import { useState, useMemo, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Search, Download, Eye,
  ChevronUp, ChevronDown,
  FileText, Filter, Plus,
} from 'lucide-react'
import { Card }      from '@/components/ui/Card'
import { Button }    from '@/components/ui/Button'
import { Badge }     from '@/components/ui/Badge'
import { RiskBadge } from '@/components/ui/Badge'
import { ROUTES }    from '@/constants/app'
import { formatDate, formatRelative, scoreToColor } from '@/utils/formatters'
import { complianceService } from '@/services/complianceService'
import { exportHistoryRowPdf } from '@/utils/exportAnalysisPdf'
import type { AnalysisHistory } from '@/types/api'
import { cn }        from '@/utils/cn'
// ── Types ──────────────────────────────────────────────────────
type SortKey = keyof Pick<AnalysisHistory, 'created_at' | 'compliance_score' | 'jurisdiction'>
type SortDir = 'asc' | 'desc'
type RiskFilter = 'all' | 'high' | 'medium' | 'low'

const PER_PAGE = 5

// ── Score badge ────────────────────────────────────────────────
function ScorePill({ score }: { score: number }) {
  return (
    <span className={cn('text-sm font-bold tabular-nums', scoreToColor(score))}>
      {score}
    </span>
  )
}

// ── Sort icon ──────────────────────────────────────────────────
function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <ChevronDown className="w-3.5 h-3.5 opacity-30" />
  return dir === 'asc'
    ? <ChevronUp className="w-3.5 h-3.5 text-brand-600" />
    : <ChevronDown className="w-3.5 h-3.5 text-brand-600" />
}

// ── Main Component ──────────────────────────────────────────────
export function ReportsPage() {
  const [search,     setSearch]     = useState('')
  const [sortKey,    setSortKey]    = useState<SortKey>('created_at')
  const [sortDir,    setSortDir]    = useState<SortDir>('desc')
  const [riskFilter, setRiskFilter] = useState<RiskFilter>('all')
  const [page,       setPage]       = useState(1)
  const [history,    setHistory]    = useState<AnalysisHistory[]>([])
  const [loading,    setLoading]    = useState(true)
  const [loadError,  setLoadError]  = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    complianceService
      .getHistory()
      .then(rows => {
        if (!cancelled) {
          setHistory(rows)
          setLoadError(null)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setHistory([])
          setLoadError(err instanceof Error ? err.message : 'Failed to load history')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // ── Toggle sort ──────────────────────────────────────────────
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(1)
  }

  // ── Filtered + sorted data ───────────────────────────────────
  const processed = useMemo(() => {
    let data = [...history]

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase()
      data = data.filter(r =>
        r.query.toLowerCase().includes(q) ||
        r.jurisdiction.toLowerCase().includes(q)
      )
    }

    // Risk filter
    if (riskFilter !== 'all') {
      data = data.filter(r => r.risk_level === riskFilter)
    }

    // Sort
    data.sort((a, b) => {
      let diff: number
      switch (sortKey) {
        case 'created_at':
          diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'compliance_score':
          diff = a.compliance_score - b.compliance_score
          break
        case 'jurisdiction':
          diff = a.jurisdiction.localeCompare(b.jurisdiction)
          break
        default:
          diff = 0
      }
      return sortDir === 'asc' ? diff : -diff
    })

    return data
  }, [history, search, riskFilter, sortKey, sortDir])

  // ── Pagination ───────────────────────────────────────────────
  const totalPages = Math.ceil(processed.length / PER_PAGE)
  const paginated  = processed.slice((page - 1) * PER_PAGE, page * PER_PAGE)

  const RISK_FILTERS: { value: RiskFilter; label: string }[] = [
    { value: 'all',    label: 'All'    },
    { value: 'high',   label: 'High'   },
    { value: 'medium', label: 'Medium' },
    { value: 'low',    label: 'Low'    },
  ]

  const COLUMNS: { key: SortKey | null; label: string; sortable: boolean }[] = [
    { key: null,               label: 'Query',        sortable: false },
    { key: 'jurisdiction',     label: 'Jurisdiction', sortable: true  },
    { key: 'compliance_score', label: 'Score',        sortable: true  },
    { key: null,               label: 'Risk',         sortable: false },
    { key: 'created_at',       label: 'Date',         sortable: true  },
    { key: null,               label: 'Actions',      sortable: false },
  ]

  return (
    <div className="space-y-5">

      {/* ── Header ───────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]">Reports</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            {loading
              ? 'Loading…'
              : `${processed.length} analysis report${processed.length !== 1 ? 's' : ''}`}
          </p>
          {loadError && (
            <p className="text-xs text-red-500 mt-1">{loadError}</p>
          )}
        </div>
        <Link to={ROUTES.ANALYZE}>
          <Button leftIcon={<Plus className="w-4 h-4" />}>
            New Analysis
          </Button>
        </Link>
      </div>

      {/* ── Filters bar ──────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)] pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search by query or jurisdiction…"
            className={cn(
              'w-full h-9 pl-9 pr-3 rounded-lg text-sm',
              'bg-[var(--bg-surface)] border border-[var(--border)]',
              'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
              'focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-[var(--accent)]',
              'transition-all',
            )}
          />
        </div>

        {/* Risk level filter */}
        <div className="flex items-center gap-1.5">
          <Filter className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
          <div className="flex gap-1">
            {RISK_FILTERS.map(f => (
              <button
                key={f.value}
                onClick={() => { setRiskFilter(f.value); setPage(1) }}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                  riskFilter === f.value
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text)] border border-[var(--border)]',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Table ────────────────────────────────────────── */}
      <Card padding="none">
        {/* Empty state */}
        {paginated.length === 0 ? (
          <div className="text-center py-16">
            <FileText className="w-12 h-12 text-[var(--text-subtle)] mx-auto mb-3" />
            <p className="font-medium text-[var(--text-muted)]">No reports found</p>
            <p className="text-sm text-[var(--text-subtle)] mt-1">
              {search ? 'Try a different search term' : 'Run your first compliance analysis'}
            </p>
            {!search && (
              <Link to={ROUTES.ANALYZE} className="inline-block mt-4">
                <Button size="sm">Start Analysis</Button>
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-[var(--bg-raised)] border-b border-[var(--border)]">
                    {COLUMNS.map(col => (
                      <th
                        key={col.label}
                        className={cn(
                          'px-5 py-3 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider',
                          col.sortable && 'cursor-pointer hover:text-[var(--text)] select-none',
                        )}
                        onClick={col.sortable && col.key ? () => handleSort(col.key!) : undefined}
                      >
                        <div className="flex items-center gap-1">
                          {col.label}
                          {col.sortable && col.key && (
                            <SortIcon
                              active={sortKey === col.key}
                              dir={sortDir}
                            />
                          )}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {paginated.map((row, i) => (
                    <motion.tr
                      key={row.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.04 }}
                      className="hover:bg-[var(--bg-raised)] transition-colors"
                    >
                      {/* Query */}
                      <td className="px-5 py-3.5 max-w-[240px]">
                        <p className="text-sm font-medium text-[var(--text)] truncate">
                          {row.query}
                        </p>
                        <p className="text-xs text-[var(--text-subtle)] mt-0.5">
                          {formatRelative(row.created_at)}
                        </p>
                      </td>

                      {/* Jurisdiction */}
                      <td className="px-5 py-3.5">
                        <Badge variant="outline">{row.jurisdiction}</Badge>
                      </td>

                      {/* Score */}
                      <td className="px-5 py-3.5">
                        <ScorePill score={row.compliance_score} />
                      </td>

                      {/* Risk */}
                      <td className="px-5 py-3.5">
                        <RiskBadge level={row.risk_level} />
                      </td>

                      {/* Date */}
                      <td className="px-5 py-3.5 text-xs text-[var(--text-muted)] tabular-nums whitespace-nowrap">
                        {formatDate(row.created_at)}
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-1">
                          <Link to={`/results/${row.id}`}>
                            <Button variant="ghost" size="icon" title="View results">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="icon"
                            title="Download PDF"
                            onClick={() => exportHistoryRowPdf(row)}
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-5 py-3.5 border-t border-[var(--border)]">
                <p className="text-xs text-[var(--text-muted)]">
                  Showing {(page - 1) * PER_PAGE + 1}–{Math.min(page * PER_PAGE, processed.length)} of {processed.length}
                </p>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  {Array.from({ length: totalPages }, (_, i) => (
                    <button
                      key={i}
                      onClick={() => setPage(i + 1)}
                      className={cn(
                        'w-8 h-8 rounded-lg text-xs font-medium transition-all',
                        page === i + 1
                          ? 'bg-brand-600 text-white shadow-sm'
                          : 'text-[var(--text-muted)] hover:bg-[var(--bg-raised)]',
                      )}
                    >
                      {i + 1}
                    </button>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}