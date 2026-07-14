import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Copy, Check, ChevronDown, BookOpen, ArrowLeft, Search, AlertTriangle,
} from 'lucide-react'
import { Card }    from '@/components/ui/Card'
import { Badge }   from '@/components/ui/Badge'
import { Button }  from '@/components/ui/Button'
import { cn }      from '@/utils/cn'
import toast       from 'react-hot-toast'
import { complianceService } from '@/services/complianceService'
import { ROUTES } from '@/constants/app'
import type { AnalyzeResponse, Citation, StoredAnalysis } from '@/types/api'

function parseSessionCitations(): Citation[] {
  const raw = sessionStorage.getItem('lexai-last-result')
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw) as StoredAnalysis | AnalyzeResponse
    const result = 'result' in parsed && parsed.result
      ? parsed.result
      : (parsed as AnalyzeResponse)
    return result.citations ?? []
  } catch {
    return []
  }
}

function CitationCard({ cite }: { cite: Citation }) {
  const [expanded, setExpanded] = useState(false)
  const [copied,   setCopied]   = useState(false)

  const handleCopy = async () => {
    const heading = cite.heading ? `, ${cite.heading}` : ''
    const text = `${cite.source_label}${heading}: "${cite.excerpt}" — ${cite.jurisdiction} [${cite.citation_id}]`
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Citation copied to clipboard!')
      setTimeout(() => setCopied(false), 2500)
    } catch {
      toast.error('Failed to copy — please copy manually')
    }
  }

  const relevancePct = Math.round(cite.similarity * 100)
  const relevanceColor =
    relevancePct >= 90 ? 'success' :
    relevancePct >= 75 ? 'primary' : 'default'

  return (
    <Card padding="none" className="overflow-hidden">
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-4 p-5 text-left hover:bg-[var(--bg-raised)] transition-colors"
      >
        <div className="shrink-0 w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-900/20 flex flex-col items-center justify-center border border-brand-100 dark:border-brand-900/30">
          <span className="text-xs font-black text-brand-600">{relevancePct}%</span>
          <span className="text-[0.55rem] text-brand-500 leading-none">match</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <Badge variant={relevanceColor as 'success' | 'primary' | 'default'}>
              {cite.citation_id}
            </Badge>
            <Badge variant="outline">{cite.jurisdiction}</Badge>
          </div>
          <p className="font-semibold text-sm text-[var(--text)] truncate">
            {cite.source_label}
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-0.5 truncate">
            {cite.heading ?? 'Retrieved passage'}
          </p>
        </div>

        <ChevronDown
          className={cn(
            'w-4 h-4 text-[var(--text-muted)] shrink-0 mt-1 transition-transform duration-200',
            expanded && 'rotate-180',
          )}
        />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-0 border-t border-[var(--border)]">
              <p className="text-sm text-[var(--text-muted)] leading-relaxed mt-4">
                {cite.excerpt}
              </p>
              <div className="mt-3 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  onClick={() => void handleCopy()}
                >
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}

export function CitationsPage() {
  const { id } = useParams<{ id: string }>()
  const [search, setSearch] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [resultId, setResultId] = useState<string | undefined>(id)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)

      if (id && /^\d+$/.test(id)) {
        try {
          const detail = await complianceService.getAnalysis(id)
          if (!cancelled) {
            setCitations(detail.result.citations ?? [])
            setResultId(detail.id)
            sessionStorage.setItem('lexai-last-result', JSON.stringify(detail))
          }
        } catch (err) {
          if (!cancelled) {
            const session = parseSessionCitations()
            if (session.length) {
              setCitations(session)
              setResultId(id)
            } else {
              setCitations([])
              setError(err instanceof Error ? err.message : 'Could not load citations')
            }
          }
        } finally {
          if (!cancelled) setLoading(false)
        }
        return
      }

      const session = parseSessionCitations()
      if (!cancelled) {
        setCitations(session)
        setResultId(
          (() => {
            try {
              const raw = sessionStorage.getItem('lexai-last-result')
              if (!raw) return undefined
              const parsed = JSON.parse(raw) as StoredAnalysis
              return parsed.id
            } catch {
              return undefined
            }
          })(),
        )
        if (!session.length) {
          setError('No citations yet — run an analysis first.')
        }
        setLoading(false)
      }
    }

    void load()
    return () => { cancelled = true }
  }, [id])

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    if (!q) return citations
    return citations.filter(c =>
      c.source_label.toLowerCase().includes(q) ||
      (c.heading?.toLowerCase().includes(q) ?? false) ||
      c.jurisdiction.toLowerCase().includes(q) ||
      c.citation_id.toLowerCase().includes(q),
    )
  }, [citations, search])

  const avgSimilarity = citations.length
    ? citations.reduce((s, c) => s + c.similarity, 0) / citations.length
    : 0

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-16 text-center text-sm text-[var(--text-muted)]">
        Loading citations…
      </div>
    )
  }

  if (error && citations.length === 0) {
    return (
      <div className="max-w-lg mx-auto py-16 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
        <h1 className="text-xl font-bold text-[var(--text)]">No citations</h1>
        <p className="text-sm text-[var(--text-muted)]">{error}</p>
        <div className="flex justify-center gap-3">
          <Link to={ROUTES.REPORTS}>
            <Button variant="outline">View reports</Button>
          </Link>
          <Link to={ROUTES.ANALYZE}>
            <Button>Run analysis</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link to={resultId ? `/results/${resultId}` : ROUTES.ANALYZE}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]">
            Citation Viewer
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            {citations.length} grounded passages · avg match {Math.round(avgSimilarity * 100)}%
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search citations by source, heading, or jurisdiction…"
          className={cn(
            'w-full pl-10 pr-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--bg-surface)]',
            'text-[var(--text)] placeholder:text-[var(--text-subtle)] text-sm',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/30',
          )}
        />
      </div>

      {filtered.length === 0 ? (
        <Card>
          <div className="py-10 text-center text-sm text-[var(--text-muted)] flex flex-col items-center gap-2">
            <BookOpen className="w-8 h-8 opacity-40" />
            No citations match your search.
          </div>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(cite => (
            <CitationCard key={cite.citation_id} cite={cite} />
          ))}
        </div>
      )}
    </div>
  )
}
