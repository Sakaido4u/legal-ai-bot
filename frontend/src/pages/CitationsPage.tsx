import { useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Copy, Check, ChevronDown, BookOpen, ArrowLeft, Search,
} from 'lucide-react'
import { Card }    from '@/components/ui/Card'
import { Badge }   from '@/components/ui/Badge'
import { Button }  from '@/components/ui/Button'
import { cn }      from '@/utils/cn'
import toast       from 'react-hot-toast'
import type { AnalyzeResponse, Citation, StoredAnalysis } from '@/types/api'

const FALLBACK_CITATIONS: Citation[] = [
  {
    citation_id: 'C0',
    jurisdiction: 'GDPR',
    source_label: 'GDPR Art. 5(1)(e)',
    heading: 'Storage limitation',
    excerpt:
      'Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed.',
    similarity: 0.91,
  },
  {
    citation_id: 'C1',
    jurisdiction: 'GDPR',
    source_label: 'GDPR Art. 7',
    heading: 'Conditions for consent',
    excerpt:
      'If the data subject\'s consent is given in the context of a written declaration which also concerns other matters, the request for consent shall be presented in a manner which is clearly distinguishable.',
    similarity: 0.87,
  },
]

function loadCitations(): Citation[] {
  const raw = sessionStorage.getItem('lexai-last-result')
  if (!raw) return FALLBACK_CITATIONS
  try {
    const parsed = JSON.parse(raw) as StoredAnalysis | AnalyzeResponse
    const result = 'result' in parsed && parsed.result
      ? parsed.result
      : (parsed as AnalyzeResponse)
    return result.citations?.length ? result.citations : FALLBACK_CITATIONS
  } catch {
    return FALLBACK_CITATIONS
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
            <div className="px-5 pb-5 space-y-4 border-t border-[var(--border)] pt-4">
              <blockquote className="relative pl-4 text-sm text-[var(--text-muted)] italic leading-relaxed">
                <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-brand-500 rounded-full" />
                "{cite.excerpt}"
              </blockquote>

              <p className="text-xs text-[var(--text-subtle)]">
                <span className="font-medium text-[var(--text-muted)]">Source: </span>
                {cite.source_label}
              </p>

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={handleCopy}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                    copied
                      ? 'bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                      : 'bg-[var(--bg-raised)] text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--border)]',
                  )}
                >
                  {copied
                    ? <><Check className="w-3.5 h-3.5" /> Copied!</>
                    : <><Copy className="w-3.5 h-3.5" /> Copy citation</>
                  }
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}

export function CitationsPage() {
  const { id }       = useParams<{ id: string }>()
  const [search, setSearch] = useState('')
  const citations = useMemo(() => loadCitations(), [])

  const filtered = citations.filter(c => {
    const q = search.toLowerCase()
    return (
      c.source_label.toLowerCase().includes(q) ||
      (c.heading?.toLowerCase().includes(q) ?? false) ||
      c.jurisdiction.toLowerCase().includes(q) ||
      c.citation_id.toLowerCase().includes(q)
    )
  })

  const avgSimilarity = citations.length
    ? citations.reduce((s, c) => s + c.similarity, 0) / citations.length
    : 0

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link to={id ? `/results/${id}` : -1 as unknown as string}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]">
            Citation Viewer
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            {citations.length} legal citations found
          </p>
        </div>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)] pointer-events-none" />
        <input
          type="search"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search citations by source, heading, or jurisdiction…"
          className={cn(
            'w-full h-10 pl-10 pr-4 rounded-xl text-sm',
            'bg-[var(--bg-surface)] border border-[var(--border)]',
            'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
            'focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-[var(--accent)]',
            'transition-all duration-150',
          )}
        />
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)]">
          <BookOpen className="w-3.5 h-3.5 text-brand-500" />
          <span className="text-xs font-medium text-[var(--text-muted)]">
            {filtered.length} citations
          </span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/40">
          <span className="text-xs font-medium text-green-700 dark:text-green-400">
            Avg similarity: {Math.round(avgSimilarity * 100)}%
          </span>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen className="w-12 h-12 text-[var(--text-subtle)] mx-auto mb-3" />
          <p className="text-[var(--text-muted)] font-medium">No citations found</p>
          <p className="text-sm text-[var(--text-subtle)] mt-1">Try a different search term</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((cite, i) => (
            <motion.div
              key={cite.citation_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <CitationCard cite={cite} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
