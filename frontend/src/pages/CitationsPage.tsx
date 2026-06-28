import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Copy, Check, ExternalLink,
  ChevronDown, BookOpen, ArrowLeft,
  Search,
} from 'lucide-react'
import { Card }    from '@/components/ui/Card'
import { Badge }   from '@/components/ui/Badge'
import { Button }  from '@/components/ui/Button'
import { cn }      from '@/utils/cn'
import toast       from 'react-hot-toast'
import type { Citation } from '@/types/api'

// ── Mock citations ─────────────────────────────────────────────
const MOCK_CITATIONS: Citation[] = [
  {
    id:              'c1',
    title:           'General Data Protection Regulation',
    section:         'Article 5(1)(e) — Storage Limitation',
    excerpt:         'Personal data shall be kept in a form which permits identification of data subjects for no longer than is necessary for the purposes for which the personal data are processed; personal data may be stored for longer periods insofar as the personal data will be processed solely for archiving purposes in the public interest.',
    source:          'European Parliament & Council of the European Union',
    url:             'https://gdpr.eu/article-5/',
    relevance_score: 0.96,
  },
  {
    id:              'c2',
    title:           'GDPR — Conditions for Consent',
    section:         'Article 7(2)',
    excerpt:         'If the data subject\'s consent is given in the context of a written declaration which also concerns other matters, the request for consent shall be presented in a manner which is clearly distinguishable from the other matters, in an intelligible and easily accessible form, using clear and plain language.',
    source:          'European Parliament & Council of the European Union',
    url:             'https://gdpr.eu/article-7/',
    relevance_score: 0.91,
  },
  {
    id:              'c3',
    title:           'ICO Guidance on Direct Marketing',
    section:         'Retention Periods for Marketing Data',
    excerpt:         'The ICO recommends that personal data used solely for direct marketing purposes should not be retained for longer than 12-13 months without refreshing consent. You should regularly review the personal data you hold and delete or anonymise data that you no longer need.',
    source:          'Information Commissioner\'s Office (ICO)',
    url:             'https://ico.org.uk/for-organisations/guide-to-data-protection/',
    relevance_score: 0.87,
  },
  {
    id:              'c4',
    title:           'GDPR — Records of Processing Activities',
    section:         'Article 30(1)',
    excerpt:         'Each controller and, where applicable, the controller\'s representative, shall maintain a record of processing activities under its responsibility. That record shall contain all of the following information: the name and contact details of the controller and, where applicable, the joint controller, the controller\'s representative and the data protection officer.',
    source:          'European Parliament & Council of the European Union',
    url:             'https://gdpr.eu/article-30/',
    relevance_score: 0.82,
  },
  {
    id:              'c5',
    title:           'EDPB Guidelines on Consent',
    section:         'Guidelines 05/2020 — Section 3.1',
    excerpt:         'Consent should be given by a clear affirmative act establishing a freely given, specific, informed and unambiguous indication of the data subject\'s agreement to the processing of personal data relating to him or her.',
    source:          'European Data Protection Board',
    url:             'https://edpb.europa.eu/our-work-tools/our-documents/guidelines/guidelines-052020-consent-under-regulation-2016679_en',
    relevance_score: 0.79,
  },
]

// ── Citation Card ──────────────────────────────────────────────
function CitationCard({ cite }: { cite: Citation }) {
  const [expanded, setExpanded] = useState(false)
  const [copied,   setCopied]   = useState(false)

  const handleCopy = async () => {
    const text = `${cite.title}, ${cite.section}: "${cite.excerpt}" — ${cite.source}`
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      toast.success('Citation copied to clipboard!')
      setTimeout(() => setCopied(false), 2500)
    } catch {
      toast.error('Failed to copy — please copy manually')
    }
  }

  const relevancePct = Math.round(cite.relevance_score * 100)
  const relevanceColor =
    relevancePct >= 90 ? 'success' :
    relevancePct >= 75 ? 'primary' : 'default'

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header button */}
      <button
        onClick={() => setExpanded(p => !p)}
        className="w-full flex items-start gap-4 p-5 text-left hover:bg-[var(--bg-raised)] transition-colors"
      >
        {/* Relevance score */}
        <div className="shrink-0 w-12 h-12 rounded-xl bg-brand-50 dark:bg-brand-900/20 flex flex-col items-center justify-center border border-brand-100 dark:border-brand-900/30">
          <span className="text-xs font-black text-brand-600">{relevancePct}%</span>
          <span className="text-[0.55rem] text-brand-500 leading-none">match</span>
        </div>

        {/* Title + section */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <Badge variant={relevanceColor as 'success' | 'primary' | 'default'}>
              {cite.section.split('—')[0]?.trim() ?? cite.section}
            </Badge>
          </div>
          <p className="font-semibold text-sm text-[var(--text)] truncate">
            {cite.title}
          </p>
          <p className="text-xs text-[var(--text-muted)] mt-0.5 truncate">
            {cite.section}
          </p>
        </div>

        {/* Expand icon */}
        <ChevronDown
          className={cn(
            'w-4 h-4 text-[var(--text-muted)] shrink-0 mt-1 transition-transform duration-200',
            expanded && 'rotate-180',
          )}
        />
      </button>

      {/* Expanded content */}
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
              {/* Excerpt */}
              <blockquote className="relative pl-4 text-sm text-[var(--text-muted)] italic leading-relaxed">
                <span className="absolute left-0 top-0 bottom-0 w-0.5 bg-brand-500 rounded-full" />
                "{cite.excerpt}"
              </blockquote>

              {/* Source */}
              <p className="text-xs text-[var(--text-subtle)]">
                <span className="font-medium text-[var(--text-muted)]">Source: </span>
                {cite.source}
              </p>

              {/* Actions */}
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

                {cite.url && (
                  <a
                    href={cite.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--bg-raised)] text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View source
                  </a>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}

// ── Main Component ──────────────────────────────────────────────
export function CitationsPage() {
  const { id }       = useParams<{ id: string }>()
  const [search, setSearch] = useState('')

  const filtered = MOCK_CITATIONS.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.section.toLowerCase().includes(search.toLowerCase()) ||
    c.source.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* ── Header ───────────────────────────────────────── */}
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
            {MOCK_CITATIONS.length} legal citations found
          </p>
        </div>
      </div>

      {/* ── Search ───────────────────────────────────────── */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-subtle)] pointer-events-none" />
        <input
          type="search"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search citations by title, section, or source…"
          className={cn(
            'w-full h-10 pl-10 pr-4 rounded-xl text-sm',
            'bg-[var(--bg-surface)] border border-[var(--border)]',
            'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
            'focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:border-[var(--accent)]',
            'transition-all duration-150',
          )}
        />
      </div>

      {/* ── Stats row ─────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--bg-raised)] border border-[var(--border)]">
          <BookOpen className="w-3.5 h-3.5 text-brand-500" />
          <span className="text-xs font-medium text-[var(--text-muted)]">
            {filtered.length} citations
          </span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-900/40">
          <span className="text-xs font-medium text-green-700 dark:text-green-400">
            Avg relevance: {Math.round(MOCK_CITATIONS.reduce((s, c) => s + c.relevance_score, 0) / MOCK_CITATIONS.length * 100)}%
          </span>
        </div>
      </div>

      {/* ── Citation cards ────────────────────────────────── */}
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
              key={cite.id}
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