// Custom hook wrapping complianceService.
// Manages loading, error, and result state.
// Components call this hook instead of the service directly.

import { useState, useCallback } from 'react'
import { complianceService } from '@/services/complianceService'
import type { AnalyzeRequest, AnalyzeResponse } from '@/types/api'
import toast from 'react-hot-toast'

export function useCompliance() {
  const [isLoading, setIsLoading] = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [result,    setResult]    = useState<AnalyzeResponse | null>(null)

  const analyze = useCallback(async (request: AnalyzeRequest) => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await complianceService.analyze(request)
      setResult(data)
      toast.success('Analysis complete!')
      return data
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Analysis failed'
      setError(msg)
      toast.error(msg)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { analyze, reset, isLoading, error, result }
}
