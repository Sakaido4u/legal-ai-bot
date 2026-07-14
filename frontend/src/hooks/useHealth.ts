// Hook for checking backend health status.
// Used on the Settings page API Status tab.

import { useState, useEffect } from 'react'
import { healthService } from '@/services/complianceService'
import type { HealthResponse } from '@/types/api'

type HealthStatus = 'idle' | 'checking' | 'healthy' | 'degraded' | 'unreachable'

export function useHealth(autoCheck = false) {
  const [status,   setStatus]   = useState<HealthStatus>('idle')
  const [details,  setDetails]  = useState<HealthResponse | null>(null)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const check = async () => {
    setStatus('checking')
    try {
      const data = await healthService.check()
      setDetails(data)
      const ok = data.status === 'healthy' || data.status === 'ok'
      setStatus(ok ? 'healthy' : data.status === 'starting' ? 'degraded' : 'degraded')
      setLastCheck(new Date())
    } catch {
      setStatus('unreachable')
      setDetails(null)
      setLastCheck(new Date())
    }
  }

  useEffect(() => {
    if (autoCheck) void check()
  }, [autoCheck])

  return { status, details, lastCheck, check }
}