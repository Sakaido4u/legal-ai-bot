import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText, Trash2, RefreshCw, Eye, X, AlertTriangle, Plus,
} from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { documentService } from '@/services/documentService'
import type { DocumentDetailResponse } from '@/services/documentService'
import type { DocumentUploadResponse } from '@/types/api'
import { formatDate } from '@/utils/formatters'
import { ROUTES } from '@/constants/app'
import { cn } from '@/utils/cn'
import toast from 'react-hot-toast'

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentUploadResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<DocumentDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [pendingDelete, setPendingDelete] = useState<DocumentUploadResponse | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await documentService.list()
      setDocs(res.documents)
    } catch (err) {
      setDocs([])
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const openDetail = async (id: number) => {
    setDetailLoading(true)
    try {
      const doc = await documentService.get(id)
      setDetail(doc)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load document')
    } finally {
      setDetailLoading(false)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return
    setDeleting(true)
    try {
      await documentService.remove(pendingDelete.id)
      toast.success(`Deleted document #${pendingDelete.id}`)
      setPendingDelete(null)
      if (detail?.id === pendingDelete.id) setDetail(null)
      await load()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-5 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text)]">Documents</h1>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            Uploaded PDFs stored in Postgres
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void load()}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            disabled={loading}
          >
            Refresh
          </Button>
          <Link to={ROUTES.ANALYZE}>
            <Button size="sm" leftIcon={<Plus className="w-3.5 h-3.5" />}>
              Upload via Analyze
            </Button>
          </Link>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-500 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </p>
      )}

      <Card padding="none">
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-2 text-sm text-[var(--text-muted)]">
            <Spinner className="w-5 h-5" />
            Loading documents…
          </div>
        ) : docs.length === 0 ? (
          <div className="text-center py-16 px-4">
            <FileText className="w-10 h-10 text-[var(--text-subtle)] mx-auto mb-3" />
            <p className="text-sm font-medium text-[var(--text)]">No documents yet</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Upload a PDF from the Analyze page.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-[var(--bg-raised)] border-b border-[var(--border)]">
                  {['ID', 'Filename', 'Jurisdiction', 'Status', 'Uploaded', 'Actions'].map(h => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {docs.map((doc, i) => (
                  <motion.tr
                    key={doc.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="hover:bg-[var(--bg-raised)] transition-colors"
                  >
                    <td className="px-4 py-3 text-xs font-mono text-[var(--text-muted)]">
                      #{doc.id}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-[var(--text)] max-w-[220px] truncate">
                      {doc.filename}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">{doc.jurisdiction}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge
                        variant={
                          doc.processing_status === 'completed' ? 'success'
                            : doc.processing_status === 'failed' ? 'danger'
                            : 'default'
                        }
                      >
                        {doc.processing_status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
                      {doc.upload_date ? formatDate(doc.upload_date) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => void openDetail(doc.id)}
                          aria-label="View document"
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setPendingDelete(doc)}
                          aria-label="Delete document"
                          className="text-red-500 hover:text-red-600"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Detail panel */}
      <AnimatePresence>
        {(detail || detailLoading) && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
          >
            <Card>
              <div className="flex items-start justify-between gap-3 mb-4">
                <div>
                  <h2 className="text-base font-bold text-[var(--text)]">
                    {detailLoading ? 'Loading…' : detail?.filename}
                  </h2>
                  {detail && (
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      Doc #{detail.id} · {detail.jurisdiction} · {detail.processing_status}
                      {detail.sha256 ? ` · ${detail.sha256.slice(0, 12)}…` : ''}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setDetail(null)}
                  aria-label="Close"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
              {detailLoading && (
                <div className="flex justify-center py-8">
                  <Spinner />
                </div>
              )}
              {detail && !detailLoading && (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {(detail.sections ?? []).length === 0 ? (
                    <p className="text-sm text-[var(--text-muted)]">No sections returned.</p>
                  ) : (
                    (detail.sections ?? []).map(section => (
                      <div
                        key={section.id}
                        className={cn(
                          'rounded-xl border border-[var(--border)] p-3',
                          'bg-[var(--bg-raised)]',
                        )}
                      >
                        <p className="text-sm font-semibold text-[var(--text)]">
                          {section.heading || `Section ${section.section_id}`}
                        </p>
                        <p className="text-xs text-[var(--text-muted)] mt-1">
                          {section.chunks.length} chunk
                          {section.chunks.length !== 1 ? 's' : ''}
                        </p>
                        {section.chunks[0]?.text && (
                          <p className="text-xs text-[var(--text-muted)] mt-2 line-clamp-4 leading-relaxed">
                            {section.chunks[0].text}
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete confirm */}
      <AnimatePresence>
        {pendingDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="card p-6 max-w-md w-full space-y-4"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <h3 className="font-bold text-[var(--text)]">Delete document?</h3>
                  <p className="text-sm text-[var(--text-muted)] mt-1">
                    This removes <span className="font-medium">{pendingDelete.filename}</span>{' '}
                    (#{pendingDelete.id}) and reindexes FAISS. This cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setPendingDelete(null)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => void confirmDelete()}
                  isLoading={deleting}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Delete
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
