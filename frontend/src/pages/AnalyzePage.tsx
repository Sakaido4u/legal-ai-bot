import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload, X, FileText, Scale, CheckCircle2,
  ChevronDown, AlertCircle, Lightbulb,
} from 'lucide-react'
import { Button }   from '@/components/ui/Button'
import { Card }     from '@/components/ui/Card'
import { Spinner }  from '@/components/ui/Spinner'
import { useCompliance } from '@/hooks/useCompliance'
import { complianceService, MOCK_JURISDICTIONS } from '@/services/complianceService'
import { documentService, validatePdfFile } from '@/services/documentService'
import type { DocumentUploadResponse, Jurisdiction } from '@/types/api'
import { cn } from '@/utils/cn'

type UploadUiStatus = 'idle' | 'uploading' | 'success' | 'error'

// ── Zod schema ────────────────────────────────────────────────
const analyzeSchema = z.object({
  query: z
    .string()
    .min(20, 'Please describe your legal query in at least 20 characters')
    .max(2000, 'Query must be under 2000 characters'),
  jurisdiction: z.string().min(1, 'Please select a jurisdiction'),
})

type AnalyzeFormData = z.infer<typeof analyzeSchema>

// ── Example queries ───────────────────────────────────────────
const EXAMPLE_QUERIES = [
  'We are processing personal data of EU citizens for marketing purposes with a 3-year retention policy. Are we GDPR compliant?',
  'Our employment contract includes a 2-year non-compete clause. Is this enforceable under Indian labour law?',
  'We want to use open-source software with an MIT license in our commercial product. What are the legal obligations?',
  'Our SaaS terms of service include a clause limiting liability to 3 months of subscription fees. Is this valid under UK consumer law?',
]

// ── Component ─────────────────────────────────────────────────
export function AnalyzePage() {
  const [uploadedFile,   setUploadedFile]   = useState<File | null>(null)
  const [isDragging,     setIsDragging]     = useState(false)
  const [jurisdictions,  setJurisdictions]  = useState<Jurisdiction[]>(MOCK_JURISDICTIONS)
  const [showExamples,   setShowExamples]   = useState(false)
  const [uploadStatus,   setUploadStatus]   = useState<UploadUiStatus>('idle')
  const [uploadError,    setUploadError]    = useState<string | null>(null)
  const [uploadResult,   setUploadResult]   = useState<DocumentUploadResponse | null>(null)
  const { analyze, isLoading } = useCompliance()
  const navigate = useNavigate()

  // Load jurisdictions from backend on mount
  useEffect(() => {
    complianceService
      .getJurisdictions()
      .then(setJurisdictions)
      .catch(() => setJurisdictions(MOCK_JURISDICTIONS))
  }, [])

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<AnalyzeFormData>({
    resolver: zodResolver(analyzeSchema),
  })

  const queryValue = watch('query', '')
  const jurisdictionValue = watch('jurisdiction', '')
  const charCount  = queryValue.length

  const resetUploadState = useCallback(() => {
    setUploadedFile(null)
    setUploadStatus('idle')
    setUploadError(null)
    setUploadResult(null)
  }, [])

  const selectFile = useCallback((file: File | undefined) => {
    if (!file) return
    const validationError = validatePdfFile(file)
    if (validationError) {
      setUploadedFile(null)
      setUploadResult(null)
      setUploadStatus('error')
      setUploadError(validationError)
      return
    }
    setUploadedFile(file)
    setUploadResult(null)
    setUploadStatus('idle')
    setUploadError(null)
  }, [])

  const handleUpload = useCallback(async () => {
    if (!uploadedFile) return
    if (!jurisdictionValue) {
      setUploadStatus('error')
      setUploadError('Select a jurisdiction before uploading.')
      return
    }

    setUploadStatus('uploading')
    setUploadError(null)
    setUploadResult(null)

    try {
      const result = await documentService.upload(
        uploadedFile,
        jurisdictionValue,
        uploadedFile.name.replace(/\.pdf$/i, ''),
      )
      setUploadResult(result)
      setUploadStatus('success')
      sessionStorage.setItem('lexai-last-document', JSON.stringify(result))
    } catch (err) {
      setUploadStatus('error')
      setUploadResult(null)
      setUploadError(
        err instanceof Error ? err.message : 'Upload failed. Please try again.',
      )
    }
  }, [uploadedFile, jurisdictionValue])

  // ── Submit ───────────────────────────────────────────────────
  const onSubmit = async (data: AnalyzeFormData) => {
    const result = await analyze({
      query: data.query,
      // Backend requires product_feature; UI uses the legal query as the feature under review.
      product_feature: data.query.slice(0, 2000),
      jurisdictions: [data.jurisdiction],
    })
    if (result) {
      const stored = {
        id: crypto.randomUUID(),
        created_at: new Date().toISOString(),
        result,
      }
      sessionStorage.setItem('lexai-last-result', JSON.stringify(stored))
      navigate(`/results/${stored.id}`)
    }
  }

  // ── Drag & drop handlers ─────────────────────────────────────
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    selectFile(e.dataTransfer.files[0])
  }, [selectFile])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => setIsDragging(false), [])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    selectFile(e.target.files?.[0])
    e.target.value = ''
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* ── Page header ──────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--text)]">
          New Compliance Analysis
        </h1>
        <p className="text-sm text-[var(--text-muted)] mt-1">
          Describe your legal question and select a jurisdiction to get an instant compliance report.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">

        {/* ── Legal Query ───────────────────────────────── */}
        <Card padding="lg">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-semibold text-[var(--text)]">
                Legal Query
                <span className="text-red-500 ml-1">*</span>
              </label>
              <button
                type="button"
                onClick={() => setShowExamples(p => !p)}
                className="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 transition-colors font-medium"
              >
                <Lightbulb className="w-3.5 h-3.5" />
                {showExamples ? 'Hide examples' : 'Show examples'}
              </button>
            </div>

            {/* Example queries */}
            <AnimatePresence>
              {showExamples && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pb-3">
                    {EXAMPLE_QUERIES.map((q, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setValue('query', q, { shouldValidate: true })
                          setShowExamples(false)
                        }}
                        className="text-left p-3 rounded-lg border border-[var(--border)] text-xs text-[var(--text-muted)] hover:border-brand-400 hover:text-[var(--text)] hover:bg-brand-50 dark:hover:bg-brand-900/10 transition-all leading-relaxed"
                      >
                        {q.slice(0, 80)}…
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Textarea */}
            <div className="relative">
              <textarea
                {...register('query')}
                rows={7}
                placeholder={
                  'Describe your legal situation, contract clause, or compliance question...\n\n' +
                  'Example: We process personal data of EU citizens for marketing with a 3-year retention policy. Are we GDPR compliant?'
                }
                className={cn(
                  'w-full rounded-xl p-4 text-sm resize-none',
                  'bg-[var(--bg)] border border-[var(--border)]',
                  'text-[var(--text)] placeholder:text-[var(--text-subtle)]',
                  'focus:outline-none focus:ring-2 focus:ring-[var(--accent)]',
                  'focus:border-[var(--accent)] transition-all duration-150',
                  'leading-relaxed',
                  errors.query && 'border-red-500 focus:ring-red-500',
                )}
              />
              {/* Character counter */}
              <span
                className={cn(
                  'absolute bottom-3 right-3 text-xs tabular-nums transition-colors',
                  charCount > 1800 ? 'text-red-500 font-medium'
                    : charCount > 1500 ? 'text-amber-500'
                    : 'text-[var(--text-subtle)]',
                )}
              >
                {charCount} / 2000
              </span>
            </div>

            {/* Error message */}
            {errors.query && (
              <p className="flex items-center gap-1.5 text-xs text-red-500">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {errors.query.message}
              </p>
            )}
          </div>
        </Card>

        {/* ── Jurisdiction selector ─────────────────────── */}
        <Card padding="lg">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-[var(--text)]">
              Jurisdiction
              <span className="text-red-500 ml-1">*</span>
            </label>
            <p className="text-xs text-[var(--text-muted)]">
              Select the legal framework to analyze your query against.
            </p>
            <div className="relative">
              <select
                {...register('jurisdiction')}
                className={cn(
                  'w-full h-11 pl-4 pr-10 rounded-xl text-sm appearance-none',
                  'bg-[var(--bg)] border border-[var(--border)]',
                  'text-[var(--text)]',
                  'focus:outline-none focus:ring-2 focus:ring-[var(--accent)]',
                  'focus:border-[var(--accent)] transition-all duration-150',
                  'cursor-pointer',
                  errors.jurisdiction && 'border-red-500 focus:ring-red-500',
                )}
              >
                <option value="">Select a jurisdiction…</option>
                {jurisdictions.map(j => (
                  <option key={j.code} value={j.code}>
                    {j.name} ({j.code})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] pointer-events-none" />
            </div>
            {errors.jurisdiction && (
              <p className="flex items-center gap-1.5 text-xs text-red-500">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                {errors.jurisdiction.message}
              </p>
            )}
          </div>
        </Card>

        {/* ── PDF Upload ────────────────────────────────── */}
        <Card padding="none">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={cn(
              'relative p-8 rounded-xl border-2 border-dashed transition-all duration-200',
              'flex flex-col items-center justify-center gap-3 text-center min-h-[140px]',
              uploadStatus === 'error' && 'border-red-400 bg-red-50/50 dark:bg-red-900/10',
              uploadStatus === 'success' && 'border-emerald-400 bg-emerald-50/50 dark:bg-emerald-900/10',
              uploadStatus !== 'error' && uploadStatus !== 'success' && (
                isDragging
                  ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/10 scale-[1.01]'
                  : 'border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-[var(--bg-raised)]'
              ),
            )}
          >
            {uploadedFile ? (
              <div className="w-full max-w-md space-y-3">
                <div className="flex items-center gap-4">
                  <div className={cn(
                    'w-12 h-12 rounded-xl flex items-center justify-center shrink-0',
                    uploadStatus === 'success'
                      ? 'bg-emerald-100 dark:bg-emerald-900/30'
                      : 'bg-brand-100 dark:bg-brand-900/30',
                  )}>
                    {uploadStatus === 'success'
                      ? <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                      : <FileText className="w-6 h-6 text-brand-600" />}
                  </div>
                  <div className="flex-1 text-left min-w-0">
                    <p className="text-sm font-medium text-[var(--text)] truncate">
                      {uploadedFile.name}
                    </p>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {(uploadedFile.size / 1024).toFixed(1)} KB · PDF
                      {uploadStatus === 'success' && uploadResult
                        ? ` · Doc #${uploadResult.id} · ${uploadResult.processing_status}`
                        : null}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={resetUploadState}
                    disabled={uploadStatus === 'uploading'}
                    className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
                    aria-label="Remove file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {uploadStatus !== 'success' && (
                  <Button
                    type="button"
                    size="sm"
                    className="w-full"
                    onClick={handleUpload}
                    isLoading={uploadStatus === 'uploading'}
                    disabled={uploadStatus === 'uploading'}
                    leftIcon={
                      uploadStatus !== 'uploading'
                        ? <Upload className="w-4 h-4" />
                        : undefined
                    }
                  >
                    {uploadStatus === 'uploading'
                      ? 'Uploading & processing…'
                      : 'Upload to server'}
                  </Button>
                )}

                {uploadStatus === 'uploading' && (
                  <p className="flex items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
                    <Spinner className="w-3.5 h-3.5" />
                    Parsing PDF and indexing — this can take a minute…
                  </p>
                )}
              </div>
            ) : (
              <>
                <div className="w-12 h-12 rounded-xl bg-[var(--bg-raised)] flex items-center justify-center">
                  <Upload className="w-6 h-6 text-[var(--text-subtle)]" />
                </div>
                <div>
                  <p className="text-sm font-medium text-[var(--text)]">
                    Drop a PDF document here, or{' '}
                    <label className="text-brand-600 cursor-pointer hover:underline font-semibold">
                      browse
                      <input
                        type="file"
                        accept="application/pdf,.pdf"
                        className="sr-only"
                        onChange={handleFileInput}
                      />
                    </label>
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Optional · PDF only · Maximum 10 MB · Select jurisdiction first
                  </p>
                </div>
              </>
            )}
          </div>

          {uploadError && (
            <p className="flex items-start gap-1.5 px-4 pb-4 text-xs text-red-500">
              <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>{uploadError}</span>
            </p>
          )}

          {uploadStatus === 'success' && uploadResult && !uploadError && (
            <p className="flex items-start gap-1.5 px-4 pb-4 text-xs text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>
                Uploaded successfully — id {uploadResult.id}, status{' '}
                {uploadResult.processing_status}
                {uploadResult.error_message
                  ? ` (${uploadResult.error_message})`
                  : ''}.
              </span>
            </p>
          )}
        </Card>

        {/* ── Tips ─────────────────────────────────────── */}
        <div className="rounded-xl bg-brand-50 dark:bg-brand-900/10 border border-brand-100 dark:border-brand-900/30 p-4">
          <div className="flex items-start gap-3">
            <Lightbulb className="w-4 h-4 text-brand-600 shrink-0 mt-0.5" />
            <div className="text-xs text-brand-700 dark:text-brand-300 space-y-1">
              <p className="font-semibold">Tips for better results:</p>
              <ul className="space-y-0.5 text-brand-600/80 dark:text-brand-400">
                <li>• Be specific about the type of data, contract, or regulation</li>
                <li>• Mention relevant dates, parties, or jurisdictions in your query</li>
                <li>• Upload related PDF documents for deeper analysis</li>
              </ul>
            </div>
          </div>
        </div>

        {/* ── Submit button ─────────────────────────────── */}
        <Button
          type="submit"
          size="lg"
          className="w-full h-12 text-base font-semibold"
          isLoading={isLoading}
          leftIcon={!isLoading ? <Scale className="w-5 h-5" /> : undefined}
        >
          {isLoading ? 'Analyzing your query…' : 'Run Compliance Analysis'}
        </Button>
      </form>

      {/* ── Full-screen loading overlay ──────────────────── */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[var(--bg)]/90 backdrop-blur-md flex items-center justify-center"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="card text-center p-10 max-w-sm w-full mx-4 shadow-2xl"
            >
              {/* Animated ring */}
              <div className="relative w-20 h-20 mx-auto mb-6">
                <div className="absolute inset-0 rounded-full border-4 border-[var(--border)]" />
                <div className="absolute inset-0 rounded-full border-4 border-t-brand-600 animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Scale className="w-7 h-7 text-brand-600" />
                </div>
              </div>
              <h3 className="font-bold text-lg text-[var(--text)] mb-2">
                Analyzing your query
              </h3>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                Checking applicable laws and regulations across the selected jurisdiction…
              </p>
              {/* Animated dots */}
              <div className="flex items-center justify-center gap-1.5 mt-4">
                {[0, 1, 2].map(i => (
                  <motion.span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-brand-400"
                    animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                    transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}